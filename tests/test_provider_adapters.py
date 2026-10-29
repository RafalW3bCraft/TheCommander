"""Optional providers: protocol contracts and routing under controlled transports."""

import json

import httpx
import pytest
from test_workflows import app as workflow_app

from commander.contracts import RunInput
from commander.errors import DomainError
from commander.preferences import resolve, values
from commander.providers import Provider
from commander.runs import enqueue
from commander.worker import Worker

app = workflow_app


@pytest.mark.parametrize("kind,model", [("openai", "gpt-4.1"), ("anthropic", "claude-sonnet-4-5")])
def test_optional_selection_validation_and_snapshot_route(app, settings, kind, model):
    client, vendor, owner, db = app
    calls = []

    def handle(request):
        body = json.loads(request.content) if request.content else {}
        calls.append((request, body))
        assert (request.headers.get("authorization") or request.headers.get("x-api-key")) in (
            "Bearer isolated-provider-key",
            "isolated-provider-key",
        )
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": model}]})
        if body.get("tools"):
            if kind == "anthropic":
                return httpx.Response(
                    200,
                    json={
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "probe",
                                "name": "validation_probe",
                                "input": {"ok": True},
                            }
                        ],
                        "stop_reason": "tool_use",
                        "usage": {"input_tokens": 12, "output_tokens": 2},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "probe",
                                        "type": "function",
                                        "function": {
                                            "name": "validation_probe",
                                            "arguments": '{"ok":true}',
                                        },
                                    }
                                ]
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 2, "total_tokens": 14},
                },
            )
        if kind == "anthropic":
            return httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": "OK"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 12, "output_tokens": 2},
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 2, "total_tokens": 14},
            },
        )

    transport = httpx.MockTransport(handle)
    # Substitute the controlled application transport, never a real provider key.
    from commander.connections import Connections
    from commander.contracts import ConnectionInput
    from commander.preferences import SettingsPatch, update

    Connections(db, settings, transport).save(
        owner, kind, ConnectionInput(secret="isolated-provider-key")
    )
    updated = update(
        db,
        settings,
        owner,
        SettingsPatch(revision=0, inference_provider=kind, provider_model=model),
        transport,
    )
    assert updated["effective"]["inference_provider"] == kind
    queued = enqueue(db, settings, owner, RunInput(prompt="Provider acceptance", mode="ask"))
    update(
        db,
        settings,
        owner,
        SettingsPatch(revision=updated["revision"], inference_provider="nebius", provider_model=""),
        vendor.transport(),
    )
    Worker(settings, transport).tick()
    assert db.one("SELECT status FROM runs WHERE id=%s", (queued["id"],))["status"] == "succeeded"
    usage = db.all("SELECT provider,model,cost_usd FROM usage WHERE run_id=%s", (queued["id"],))
    assert (
        usage[0]["provider"] == kind and usage[0]["model"] == model and usage[0]["cost_usd"] is None
    )
    assert all(request.url.host == f"api.{kind}.com" for request, _ in calls)
    Connections(db, settings, transport).revoke(owner, kind)
    assert resolve(db, settings, owner, queued["settings_snapshot"]).inference_provider == kind


def test_old_snapshot_cannot_silently_route_to_current_optional_provider(app, settings):
    client, vendor, owner, db = app
    from commander.db import json as dbjson

    db.one(
        "INSERT INTO owner_settings(owner_id,preferences) VALUES (%s,%s) RETURNING owner_id",
        (owner, dbjson({"inference_provider": "openai", "provider_model": "gpt-4.1"})),
    )
    old = values(settings)
    old.pop("inference_provider")
    old.pop("provider_model")
    assert resolve(db, settings, owner, old).inference_provider == "nebius"
    # Null snapshots predate provider routing and must also preserve Nebius.
    queued = db.one(
        "INSERT INTO runs(owner_id,skill,skill_version,prompt) VALUES (%s,'conversation','conversation-v1','legacy') RETURNING *",
        (owner,),
    )
    Worker(settings, vendor.transport()).tick()
    assert db.one("SELECT status FROM runs WHERE id=%s", (queued["id"],))["status"] == "succeeded"
    assert all("openai" not in url for _, url, _ in vendor.calls)


def test_anthropic_transcript_tools_usage_and_refusals(settings):
    sent = []
    answer = {
        "content": [
            {"type": "tool_use", "id": "tool-1", "name": "search", "input": {"query": "docs"}}
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 2, "output_tokens": 3, "cache_read_input_tokens": 4},
    }

    def handle(request):
        sent.append(json.loads(request.content))
        assert request.headers["x-api-key"] == "isolated-key"
        assert "authorization" not in request.headers
        return httpx.Response(200, json=answer)

    provider = Provider(
        settings.model_copy(
            update={"inference_provider": "anthropic", "provider_model": "claude-sonnet-4-5"}
        ),
        httpx.MockTransport(handle),
    )
    transcript = [
        {"role": "system", "content": "Safe system"},
        {"role": "user", "content": "Read"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "prior", "function": {"name": "search", "arguments": '{"query":"q"}'}}
            ],
        },
        {"role": "tool", "tool_call_id": "prior", "content": "Untrusted result"},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    message, usage, _ = provider.completion("isolated-key", transcript, tools)
    assert sent[0]["system"] == "Safe system"
    assert sent[0]["messages"][-1]["content"][0]["type"] == "tool_result"
    assert sent[0]["tools"][0]["input_schema"] == tools[0]["function"]["parameters"]
    assert message["tool_calls"][0]["function"]["name"] == "search"
    assert usage["total_tokens"] == 9
    for reason in ("max_tokens", "refusal", "pause_turn"):
        answer["stop_reason"] = reason
        with pytest.raises(DomainError, match="refused or did not finish"):
            provider.completion("isolated-key", transcript)
    answer.update(stop_reason="end_turn", content=[{"type": "text", "text": "OK"}], usage=None)
    assert provider.completion("isolated-key", transcript)[1] is None
    answer["usage"] = {"input_tokens": True, "output_tokens": 2}
    with pytest.raises(DomainError, match="invalid usage"):
        provider.completion("isolated-key", transcript)


def test_openai_requests_never_fallback_and_preserve_unknown_usage(settings):
    calls = []
    answer = {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]}

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=answer)

    provider = Provider(
        settings.model_copy(update={"inference_provider": "openai", "provider_model": "gpt-4.1"}),
        httpx.MockTransport(handle),
    )
    _, usage, _ = provider.completion("isolated-key", [{"role": "user", "content": "Question"}])
    body = json.loads(calls[0].content)
    assert body["store"] is False and body["max_completion_tokens"] == settings.max_output_tokens
    assert "temperature" not in body and usage is None
    answer["choices"][0]["message"]["refusal"] = "No"
    with pytest.raises(DomainError):
        provider.completion("isolated-key", [{"role": "user", "content": "Question"}])
    assert len(calls) == 2 and all(r.url.host == "api.openai.com" for r in calls)


def test_optional_model_without_tool_capability_is_not_saved(app, settings):
    client, vendor, owner, db = app
    from commander.connections import Connections
    from commander.contracts import ConnectionInput
    from commander.preferences import SettingsPatch, update, view

    def handle(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "gpt-4.1"}]})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "I cannot call tools"}, "finish_reason": "stop"}
                ]
            },
        )

    transport = httpx.MockTransport(handle)
    Connections(db, settings, transport).save(
        owner, "openai", ConnectionInput(secret="isolated-provider-key")
    )
    with pytest.raises(DomainError, match="tool"):
        update(
            db,
            settings,
            owner,
            SettingsPatch(revision=0, inference_provider="openai", provider_model="gpt-4.1"),
            transport,
        )
    assert view(db, settings, owner)["effective"]["inference_provider"] == "nebius"
