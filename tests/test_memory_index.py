"""Controlled transports/backends: these tests do not establish live Mem0 retrieval quality."""

import secrets
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from commander.memory_index import IndexUnavailable, MemoryIndex
from memory_service.app import RevisionConflict, create_app
from memory_service.backend import DIMENSIONS, MODEL, REVISION, Mem0Index
from memory_service.contracts import Record, RevisionedKey, Search


@pytest.fixture
def token():
    return secrets.token_urlsafe(32)


class Store:
    def __init__(self):
        self.connection_pool = SimpleNamespace(close=lambda: None)
        self.records = {}
        self.search_filters = []

    def get(self, key):
        return self.records.get(key)

    def update(self, key, vector, payload):
        self.records[key] = SimpleNamespace(id=key, payload=payload, score=0.7)

    def insert(self, vectors, payloads, ids):
        for key, vector, payload in zip(ids, vectors, payloads):
            self.update(key, vector, payload)

    def delete(self, key):
        self.records.pop(key, None)

    def search(self, query, vector, top_k, filters):
        self.search_filters.append(filters)
        # Deliberately return other scopes too; backend must reject them again.
        return list(self.records.values())

    def keyword_search(self, query, top_k, filters):
        self.search_filters.append(filters)
        return list(self.records.values())

    def col_info(self):
        return {"count": len(self.records)}


class Embedder:
    max_seq_length = 512

    def __init__(self):
        self.inputs = []

    def tokenizer(self, text, **kwargs):
        return {"input_ids": text.split()}

    def encode(self, text, **kwargs):
        assert kwargs == {"normalize_embeddings": True, "show_progress_bar": False}
        self.inputs.append(text)
        return SimpleNamespace(tolist=lambda: [0.0] * DIMENSIONS)


class Locks:
    def __init__(self):
        self.calls = []

    def close(self):
        pass

    @contextmanager
    def connection(self):
        yield self

    def execute(self, sql, params):
        self.calls.append((sql, params))


@pytest.fixture
def backend():
    return Mem0Index(Store(), Embedder(), Locks())


def record(**overrides):
    return Record.model_validate(
        {
            "id": str(uuid4()),
            "owner_id": str(uuid4()),
            "project_id": str(uuid4()),
            "revision": 1,
            "text": "Prefer reviewed Python changes.",
            **overrides,
        }
    )


def test_private_service_auth_and_redaction(backend, token):
    app = create_app(backend=backend, token=token)
    with TestClient(app) as client:
        value = record()
        assert (
            client.post("/v1/records/upsert", json=value.model_dump(mode="json")).status_code == 401
        )
        headers = {"Authorization": "Bearer " + token}
        assert client.get("/health", headers=headers).json()["dimensions"] == 384
        bad = value.model_dump(mode="json") | {"unexpected_secret": "never-echo-this"}
        response = client.post("/v1/records/upsert", headers=headers, json=bad)
        assert response.status_code == 422
        assert "never-echo-this" not in response.text
        response = client.post("/v1/search", headers=headers, content=b"a" * 33000)
        assert response.status_code == 413
        assert not backend.store.records


def test_service_roundtrip_and_client_scope(backend, token):
    with TestClient(create_app(backend=backend, token=token)) as server:
        seen = []

        def dispatch(req):
            seen.append(req)
            response = server.request(
                req.method, req.url.path, content=req.content, headers=dict(req.headers)
            )
            return httpx.Response(response.status_code, content=response.content)

        client = MemoryIndex(
            "http://memory-index:8090", token, transport=httpx.MockTransport(dispatch)
        )
        a = record()
        client.upsert(a.owner_id, a.project_id, a.id, 1, a.text)
        hits = client.search(a.owner_id, a.project_id, "Python")
        assert [(x.id, x.revision) for x in hits] == [(str(a.id), 1)]
        assert not hasattr(hits[0], "text")
        client.delete(a.owner_id, a.project_id, a.id, 2)
        assert client.search(a.owner_id, a.project_id, "Python") == []
        assert all(r.headers["Authorization"] == "Bearer " + token for r in seen)


def test_stale_revision_and_same_revision_different_content_rejected(backend):
    a = record(revision=2)
    backend.upsert(a)
    for revision, text in [(1, "Old fact"), (2, "Changed fact")]:
        with pytest.raises(RevisionConflict):
            backend.upsert(a.model_copy(update={"revision": revision, "text": text}))
    backend.upsert(a)
    assert backend.store.get(backend.key(a)).payload["revision"] == 2
    assert len(backend.lock_pool.calls) == 4


def test_owner_project_filters_and_namespaced_deletion(backend):
    a = record()
    for value in [
        a,
        a.model_copy(update={"owner_id": uuid4()}),
        a.model_copy(update={"project_id": uuid4()}),
        a.model_copy(update={"project_id": None}),
    ]:
        backend.upsert(value)
    query = Search(owner_id=a.owner_id, project_id=a.project_id, query="Python")
    hits = backend.search(query)["hits"]
    assert len(hits) == 1
    assert (
        backend.store.search_filters
        == [{"owner_id": str(a.owner_id), "project_id": str(a.project_id), "deleted": False}] * 2
    )
    assert len(backend.store.records) == 4
    backend.delete(RevisionedKey(owner_id=a.owner_id, project_id=a.project_id, id=a.id, revision=2))
    assert len(backend.store.records) == 4
    assert backend.store.get(backend.key(a)).payload["deleted"] is True
    with pytest.raises(RevisionConflict):
        backend.upsert(a)
    assert backend.search(query)["hits"] == []


def test_local_embedding_prefixes_and_disclosed_truncation(backend):
    backend.vector("Hello")
    backend.vector("Hello", query=True)
    assert backend.embedder.inputs == ["passage: Hello", "query: Hello"]
    _, truncated = backend.vector("word " * 512)
    assert truncated is True
    assert MODEL == "intfloat/multilingual-e5-small"
    assert REVISION == "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    assert DIMENSIONS == 384


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503, text="sensitive upstream failure"),
        httpx.Response(302, headers={"location": "https://example.com/collect"}),
        httpx.Response(200, json={"hits": [{"id": str(uuid4()), "revision": 0, "score": 0.5}]}),
        httpx.Response(200, json={"hits": [], "secret": "not allowed"}),
        httpx.Response(200, content=b"x" * 33000),
    ],
)
def test_client_rejects_errors_redirects_and_malformed_payloads(token, response):
    calls = []

    def transport(req):
        calls.append(req)
        return response

    client = MemoryIndex(
        "http://memory-index:8090", token, transport=httpx.MockTransport(transport)
    )
    with pytest.raises(IndexUnavailable) as exc:
        client.search(uuid4(), None, "preferences")
    assert "sensitive" not in str(exc.value)
    assert len(calls) == 1


def test_client_invalid_settings_and_no_request_on_invalid_input(token):
    for url in [
        "http://public.example",
        "file:///tmp/index",
        "https://user:pass@example.com",
        "https://example.com/?token=bad",
    ]:
        with pytest.raises(ValueError):
            MemoryIndex(url, token)
    with pytest.raises(ValueError):
        create_app(token="short")
    calls = []
    client = MemoryIndex(
        "http://localhost:8090", token, transport=httpx.MockTransport(lambda req: calls.append(req))
    )
    for query, limit in [("", 5), ("query", 21)]:
        with pytest.raises(ValueError):
            client.search(uuid4(), None, query, limit)
    assert not calls


def test_backend_failure_is_redacted_and_no_partial_hybrid_claim(backend, token, monkeypatch):
    monkeypatch.setattr(backend.store, "keyword_search", lambda *a, **kw: None)
    with TestClient(create_app(backend=backend, token=token)) as client:
        response = client.post(
            "/v1/search",
            json={"owner_id": str(uuid4()), "query": "query"},
            headers={"Authorization": "Bearer " + token},
        )
        assert response.status_code == 503
        assert response.json() == {"detail": "Derived memory unavailable"}


def test_tombstone_ordering_expiry_renewal_and_old_delete(backend):
    value = record(revision=2)
    backend.upsert(value)
    key = RevisionedKey(
        owner_id=value.owner_id, project_id=value.project_id, id=value.id, revision=2
    )
    backend.delete(key)
    assert "text_lemmatized" not in backend.store.get(backend.key(value)).payload
    with pytest.raises(RevisionConflict):
        backend.upsert(value)
    renewed = value.model_copy(update={"revision": 3})
    backend.upsert(renewed)
    with pytest.raises(RevisionConflict):
        backend.delete(key)
    assert backend.store.get(backend.key(value)).payload["revision"] == 3
    assert backend.store.get(backend.key(value)).payload["deleted"] is False


def test_missing_success_ack_is_not_indexed(token):
    client = MemoryIndex(
        "http://localhost:8090",
        token,
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={})),
    )
    with pytest.raises(IndexUnavailable):
        client.upsert(uuid4(), None, uuid4(), 1, "Reviewed fact")
    with pytest.raises(IndexUnavailable):
        client.delete(uuid4(), None, uuid4(), 2)
