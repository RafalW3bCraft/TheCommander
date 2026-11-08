"""Private derived-index client. Returned IDs are hints, never authoritative memory."""

from dataclasses import dataclass
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class IndexUnavailable(Exception):
    """Index unavailable/malformed; caller must report degraded canonical recall."""


class _Hit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    revision: int = Field(ge=1, strict=True)
    score: float = Field(ge=0, le=1, allow_inf_nan=False)


class _Results(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hits: list[_Hit] = Field(max_length=20)
    query_truncated: bool = Field(strict=True)


@dataclass(frozen=True)
class IndexHit:
    id: str
    revision: int
    score: float


class MemoryIndex:
    def __init__(self, url: str, token: str, transport=None):
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or (
                parsed.scheme == "http"
                and parsed.hostname not in {"memory-index", "localhost", "127.0.0.1", "::1"}
            )
            or len(token) < 32
            or any(c.isspace() for c in token)
        ):
            raise ValueError("Explicit private index URL and strong service token required")
        self.url = url.rstrip("/")
        self._token = token
        self._transport = transport

    def _request(self, path: str, body: dict) -> dict:
        try:
            with httpx.Client(
                timeout=httpx.Timeout(15, connect=3),
                transport=self._transport,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                with client.stream(
                    "POST",
                    self.url + path,
                    headers={"Authorization": "Bearer " + self._token},
                    json=body,
                ) as response:
                    response.raise_for_status()
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > 32768:
                            raise IndexUnavailable("Derived memory response exceeded limit")
                    import json

                    result = json.loads(chunks)
                    if not isinstance(result, dict):
                        raise ValueError("Invalid response")
                    return result
        except (httpx.HTTPError, ValueError):
            # Do not propagate response bodies, addresses, credentials or provider text.
            raise IndexUnavailable("Derived memory unavailable; use canonical recall") from None

    @staticmethod
    def _scope(owner, project_id):
        return {
            "owner_id": str(UUID(str(owner))),
            "project_id": str(UUID(str(project_id))) if project_id is not None else None,
        }

    def upsert(self, owner, project_id, memory_id, revision: int, text: str) -> bool:
        if type(revision) is not int or not 1 <= revision or not text.strip() or len(text) > 4000:
            raise ValueError("Invalid canonical memory")
        result = self._request(
            "/v1/records/upsert",
            {
                **self._scope(owner, project_id),
                "id": str(UUID(str(memory_id))),
                "revision": revision,
                "text": text,
            },
        )

        if (
            set(result) != {"status", "truncated"}
            or result["status"] != "indexed"
            or type(result["truncated"]) is not bool
        ):
            raise IndexUnavailable("Invalid index acknowledgement")
        return result["truncated"]

    def delete(self, owner, project_id, memory_id, revision: int) -> None:
        if type(revision) is not int or revision < 1:
            raise ValueError("Invalid deletion revision")
        result = self._request(
            "/v1/records/delete",
            {
                **self._scope(owner, project_id),
                "id": str(UUID(str(memory_id))),
                "revision": revision,
            },
        )

        if result != {"status": "deleted"}:
            raise IndexUnavailable("Invalid deletion acknowledgement")

    def search(self, owner, project_id, query: str, limit: int = 5) -> list[IndexHit]:
        return self.search_with_status(owner, project_id, query, limit)[0]

    def search_with_status(
        self, owner, project_id, query: str, limit: int = 5
    ) -> tuple[list[IndexHit], bool]:
        if not query.strip() or len(query) > 2000 or not 1 <= limit <= 20:
            raise ValueError("Invalid memory search")
        data = self._request(
            "/v1/search", {**self._scope(owner, project_id), "query": query, "limit": limit}
        )
        try:
            results = _Results.model_validate(data)
            if len(results.hits) > limit or len({str(hit.id) for hit in results.hits}) != len(
                results.hits
            ):
                raise ValueError("Invalid result count")
            return [
                IndexHit(str(hit.id), hit.revision, hit.score) for hit in results.hits
            ], results.query_truncated
        except (ValidationError, ValueError):
            raise IndexUnavailable("Invalid derived memory response") from None
