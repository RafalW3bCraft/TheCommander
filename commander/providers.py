"""Constrained vendor HTTP contracts. No arbitrary URL fetching or redirects."""

import json
import time
from urllib.parse import urlparse

import httpx

from commander.errors import DomainError


class ProviderError(DomainError):
    pass


class Provider:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport

    def request(self, method, url, secret, body=None, *, retry=False, timeout=30):
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname
            not in {
                "api.github.com",
                "api.tavily.com",
                "api.tokenfactory.nebius.com",
                "api.tokenfactory.us-central1.nebius.com",
            }
            or parsed.username
            or parsed.port not in (None, 443)
        ):
            raise ProviderError("Destination denied", 403, "destination_denied")
        headers = {"Authorization": "Bearer " + secret, "Accept": "application/json"}
        if parsed.hostname == "api.github.com":
            headers.update(
                {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
            )
        for attempt in range(2 if retry else 1):
            try:
                with httpx.Client(
                    transport=self.transport, timeout=timeout, follow_redirects=False
                ) as client:
                    with client.stream(method, url, headers=headers, json=body) as response:
                        if response.status_code >= 300:
                            status = response.status_code
                            if retry and attempt == 0 and (status == 429 or status >= 500):
                                time.sleep(0.2)
                                continue
                            code = {
                                401: "invalid_credentials",
                                403: "insufficient_scope",
                                404: "unavailable_resource",
                                429: "rate_limited",
                                432: "budget_exceeded",
                                433: "budget_exceeded",
                            }.get(status, "provider_error")
                            raise ProviderError(
                                f"Provider request failed ({status}). Check connection permissions and status.",
                                502,
                                code,
                            )
                        chunks = []
                        size = 0
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > 1_000_000:
                                raise ProviderError(
                                    "Provider response exceeded size limit",
                                    502,
                                    "oversized_response",
                                )
                            chunks.append(chunk)
                        return json.loads(b"".join(chunks))
            except (httpx.TimeoutException, httpx.NetworkError):
                if retry and attempt == 0:
                    continue
                raise ProviderError(
                    "Provider did not return a confirmed response", 502, "transport_uncertain"
                ) from None
            except (ValueError, httpx.RemoteProtocolError):
                raise ProviderError(
                    "Provider returned malformed data", 502, "malformed_response"
                ) from None
        raise ProviderError("Provider unavailable", 502)

    def completion(self, secret, messages, tools=None, timeout=30):
        body = {
            "model": self.settings.nebius_model,
            "messages": messages,
            "max_tokens": self.settings.max_output_tokens,
            "temperature": 0.2,
        }
        if tools:
            body["tools"] = tools
        start = time.monotonic()
        data = self.request(
            "POST",
            self.settings.nebius_base_url.rstrip("/") + "/chat/completions",
            secret,
            body,
            timeout=timeout,
        )
        try:
            choice = data["choices"][0]
            message = choice["message"]
            finish = choice["finish_reason"]
            if finish not in ("stop", "tool_calls") or message.get("refusal"):
                raise ProviderError(
                    "Model refused or did not finish within the output budget",
                    502,
                    "incomplete_output",
                )
            if not isinstance(message.get("content", ""), (str, type(None))) or not (
                message.get("content") or message.get("tool_calls")
            ):
                raise ValueError()
            return message, data.get("usage"), round((time.monotonic() - start) * 1000)
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError(
                "Model returned an invalid completion", 502, "malformed_response"
            ) from None

    def github_read(self, secret, repo):
        return self.request(
            "GET",
            f"https://api.github.com/repos/{repo}/issues?state=all&per_page=20",
            secret,
            retry=True,
        )

    def search(self, secret, query, domains):
        return self.request(
            "POST",
            "https://api.tavily.com/search",
            secret,
            {
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
                "include_domains": domains,
                "include_answer": False,
                "include_raw_content": False,
            },
            retry=True,
        )
