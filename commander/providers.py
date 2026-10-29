"""Constrained vendor HTTP contracts. No arbitrary URL fetching or redirects."""

import json
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from commander.errors import DomainError
from commander.settings import inference_endpoint, inference_model


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
                "api.openai.com",
                "api.anthropic.com",
                "api.tavily.com",
                "api.tokenfactory.nebius.com",
                "api.tokenfactory.us-central1.nebius.com",
            }
            or parsed.username
            or parsed.port not in (None, 443)
        ):
            raise ProviderError("Destination denied", 403, "destination_denied")
        headers = {"Authorization": "Bearer " + secret, "Accept": "application/json"}
        if parsed.hostname == "api.anthropic.com":
            headers = {
                "x-api-key": secret,
                "anthropic-version": "2023-06-01",
                "Accept": "application/json",
            }
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
        if self.settings.inference_provider == "anthropic":
            return self._anthropic_completion(secret, messages, tools, timeout)
        if self.settings.inference_provider not in ("nebius", "openai"):
            raise ProviderError("Unsupported inference provider", 422, "unsupported_provider")
        body = {
            "model": inference_model(self.settings),
            "messages": messages,
            "max_tokens": self.settings.max_output_tokens,
            "temperature": 0.2,
        }
        if self.settings.inference_provider == "openai":
            body["max_completion_tokens"] = body.pop("max_tokens")
            body.pop("temperature")
            body["store"] = False
        if tools:
            body["tools"] = tools
        start = time.monotonic()
        data = self.request(
            "POST",
            inference_endpoint(self.settings).rstrip("/") + "/chat/completions",
            secret,
            body,
            timeout=timeout,
        )
        try:
            if not isinstance(data, dict):
                raise ValueError()
            choice = data["choices"][0]
            message = choice["message"]
            if not isinstance(message, dict):
                raise ValueError()
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

    def _anthropic_completion(self, secret, messages, tools, timeout):
        """Translate the application tool transcript into native Messages blocks."""
        body = {
            "model": inference_model(self.settings),
            "max_tokens": self.settings.max_output_tokens,
        }
        system = []
        turns: list[dict[str, Any]] = []
        try:
            for message in messages:
                role = message["role"]
                if role == "system":
                    system.append(message["content"])
                    continue
                if role == "tool":
                    blocks = [
                        {
                            "type": "tool_result",
                            "tool_use_id": message["tool_call_id"],
                            "content": message["content"],
                        }
                    ]
                    role = "user"
                elif role in ("assistant", "user"):
                    blocks = []
                    if message.get("content"):
                        blocks.append({"type": "text", "text": message["content"]})
                    for tool in message.get("tool_calls", []):
                        arguments = json.loads(tool["function"]["arguments"])
                        if not isinstance(arguments, dict):
                            raise ValueError()
                        blocks.append(
                            {
                                "type": "tool_use",
                                "id": tool["id"],
                                "name": tool["function"]["name"],
                                "input": arguments,
                            }
                        )
                else:
                    raise ValueError()
                if turns and turns[-1]["role"] == role:
                    turns[-1]["content"].extend(blocks)
                else:
                    turns.append({"role": role, "content": blocks})
            body["messages"] = turns
            if system:
                body["system"] = "\n\n".join(system)
            if tools:
                body["tools"] = [
                    {
                        "name": tool["function"]["name"],
                        "description": tool["function"].get("description", ""),
                        "input_schema": tool["function"]["parameters"],
                    }
                    for tool in tools
                ]
        except (KeyError, TypeError, ValueError):
            raise ProviderError(
                "Invalid application tool transcript", 422, "invalid_transcript"
            ) from None
        start = time.monotonic()
        data = self.request(
            "POST", "https://api.anthropic.com/v1/messages", secret, body, timeout=timeout
        )
        try:
            if not isinstance(data, dict) or not isinstance(data.get("content"), list):
                raise ValueError()
            if data.get("stop_reason") not in ("end_turn", "tool_use"):
                raise ProviderError(
                    "Model refused or did not finish within the output budget",
                    502,
                    "incomplete_output",
                )
            content, calls = [], []
            for block in data["content"]:
                if block["type"] == "text" and isinstance(block.get("text"), str):
                    content.append(block["text"])
                elif (
                    block["type"] == "tool_use"
                    and isinstance(block.get("input"), dict)
                    and isinstance(block.get("id"), str)
                    and isinstance(block.get("name"), str)
                ):
                    calls.append(
                        {
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block["input"]),
                            },
                        }
                    )
                else:
                    raise ValueError()
            if not content and not calls:
                raise ValueError()
            if (data["stop_reason"] == "tool_use") != bool(calls):
                raise ValueError()
            message = {"role": "assistant", "content": "\n".join(content)}
            if calls:
                message["tool_calls"] = calls
            usage = data.get("usage")
            if usage is not None:
                if not isinstance(usage, dict):
                    raise ValueError()
                counts = [
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                    usage.get("cache_creation_input_tokens", 0),
                    usage.get("cache_read_input_tokens", 0),
                ]
                if any(type(n) is not int or n < 0 for n in counts):
                    raise ProviderError(
                        "Provider returned invalid usage; consumption remains unknown",
                        502,
                        "malformed_usage",
                    )
                prompt = counts[0] + counts[2] + counts[3]
                usage = {
                    "prompt_tokens": prompt,
                    "completion_tokens": counts[1],
                    "total_tokens": prompt + counts[1],
                    "provider_usage": usage,
                }
            return message, usage, round((time.monotonic() - start) * 1000)
        except (KeyError, TypeError, ValueError):
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
        result = self.request(
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
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("results"), list)
            or any(
                not isinstance(row, dict)
                or any(not isinstance(row.get(key), str) for key in ("url", "title", "content"))
                for row in result["results"]
            )
        ):
            raise ProviderError(
                "Search provider returned malformed evidence", 502, "malformed_response"
            )
        return result
