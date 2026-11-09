"""Trusted driver policy with a Playwright double: no live browser claims."""

import hashlib
import importlib.util
import json
import sys
from types import SimpleNamespace
from urllib.parse import urlencode
from uuid import uuid4

import pytest

ORIGIN = "https://fixture.example.com"
PAGE_HASH = hashlib.sha256(b"controlled-page-html").hexdigest()
STATE = "c" * 64


@pytest.fixture
def browser_driver(monkeypatch):
    requests, actions = [], []
    frame = object()
    context = SimpleNamespace()

    class Route:
        def __init__(self, method, url=None, body=None, redirected=False, resource="document"):
            self.request = SimpleNamespace(
                url=url or task["url"],
                method=method,
                post_data=body,
                headers={"content-type": "application/x-www-form-urlencoded"},
                resource_type=resource,
                frame=frame,
                redirected_from=object() if redirected else None,
            )

        def abort(self):
            requests.append((self.request.method, self.request.url, "denied", None))

        def continue_(self, **kwargs):
            requests.append((self.request.method, self.request.url, "allowed", kwargs))

    task = payload()

    class Locator:
        def __init__(self, selector):
            self.selector = selector

        def count(self):
            return 1

        def fill(self, value):
            actions.append(("fill", value))
            context.handler(
                Route("POST", ORIGIN + "/fixture/commit", urlencode({"message": value}))
            )

        def click(self):
            actions.append(("click", None))
            body = task["authorization"]["body"]
            context.handler(Route("POST", ORIGIN + "/unrelated", body))
            context.handler(Route("POST", ORIGIN + "/fixture/commit", body + "x"))
            context.handler(Route("POST", ORIGIN + "/fixture/commit", body))
            context.handler(Route("POST", ORIGIN + "/fixture/commit", body))

        def evaluate_all(self, script):
            return []

        def inner_text(self):
            if self.selector == "#revision":
                return STATE
            if self.selector == "#receipt":
                return json.dumps(
                    {
                        "operation_id": task["authorization"]["operation_id"],
                        "status": "committed",
                        "writes": 1,
                        "message_sha256": hashlib.sha256(b"Demo").hexdigest(),
                    }
                )
            return "Controlled page"

    class Page:
        url = ""
        main_frame = frame

        def on(self, *args):
            pass

        def set_default_timeout(self, value):
            pass

        def goto(self, url, **kwargs):
            self.url = url
            context.handler(Route("POST", ORIGIN + "/fixture/commit", "message=Demo"))
            context.handler(Route("GET", url))
            context.handler(Route("GET", ORIGIN + "/delete?all=true"))
            context.handler(Route("GET", url, redirected=True))
            context.handler(Route("GET", url, resource="script"))

        def wait_for_timeout(self, value):
            pass

        def content(self):
            return "controlled-page-html"

        def locator(self, selector):
            return Locator(selector)

        def screenshot(self, **kwargs):
            return b"\xff\xd8\xffcontrolled-fixture"

        def title(self):
            return "Controlled"

    class Context:
        def route(self, pattern, handler):
            context.handler = handler

        def route_web_socket(self, *args):
            pass

        def new_page(self):
            return Page()

        def on(self, *args):
            pass

    class Browser:
        def new_context(self, **kw):
            assert kw["service_workers"] == "block" and not kw["accept_downloads"]
            return Context()

        def close(self):
            pass

    class Playwright:
        def __enter__(self):
            return SimpleNamespace(chromium=self)

        def __exit__(self, *args):
            pass

        def launch(self, **kwargs):
            assert kwargs["chromium_sandbox"]
            assert kwargs["proxy"]["server"] == "http://egress:3128"
            return Browser()

    monkeypatch.setitem(sys.modules, "playwright", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", SimpleNamespace(sync_playwright=Playwright)
    )
    spec = importlib.util.spec_from_file_location(
        "controlled_browser_driver", "deploy/sandbox/browser.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def execute(value):
        task.clear()
        task.update(value)
        return module.execute(task)

    return execute, requests, actions


def payload(**overrides):
    return {
        "url": "https://example.com/",
        "domains": ["example.com", "fixture.example.com"],
        "approved": False,
        "steps": [],
        "expected_page_sha256": PAGE_HASH,
        "expected_url": "https://example.com/",
        **overrides,
    }


def approved_payload(**overrides):
    return (
        payload(
            url=ORIGIN + "/fixture",
            expected_url=ORIGIN + "/fixture",
            approved=True,
            policy={"read_urls": [ORIGIN + "/fixture"], "fixture_origin": ORIGIN},
            steps=[
                {"action": "fill", "selector": "#message", "value": "Demo"},
                {"action": "click", "selector": "#submit", "value": ""},
            ],
            authorization={
                "method": "POST",
                "url": ORIGIN + "/fixture/commit",
                "body": "message=Demo",
                "headers": {"content-type": "application/x-www-form-urlencoded"},
                "operation_id": str(uuid4()),
                "page_sha256": PAGE_HASH,
                "fixture_state": STATE,
                "message_sha256": hashlib.sha256(b"Demo").hexdigest(),
            },
        )
        | overrides
    )


def test_observation_blocks_posts_redirects_resources_and_unreviewed_get(browser_driver):
    execute, requests, actions = browser_driver
    result = execute(payload())
    assert not actions and result["actions_executed"] == 0
    assert len([r for r in requests if r[2] == "allowed"]) == 1
    assert requests[1][:3] == ("GET", "https://example.com/", "allowed")
    assert (
        result["screenshot_sha256"] == hashlib.sha256(b"\xff\xd8\xffcontrolled-fixture").hexdigest()
    )


def test_fill_keeps_writes_blocked_and_click_consumes_one_exact_request(browser_driver):
    execute, requests, actions = browser_driver
    task = approved_payload()
    result = execute(task)
    writes = [r for r in requests if r[0] == "POST"]
    assert len([r for r in writes if r[2] == "allowed"]) == 1
    assert writes[1][2] == "denied"  # fill event cannot dispatch even the exact request
    allowed = next(r for r in writes if r[2] == "allowed")
    assert (
        allowed[3]["headers"]["x-commander-operation-id"] == task["authorization"]["operation_id"]
    )
    assert allowed[3]["headers"]["if-match"] == STATE
    assert result["write_receipt"]["writes"] == 1
    assert actions == [("fill", "Demo"), ("click", None)]


@pytest.mark.parametrize(
    "changed", [{"expected_page_sha256": "a" * 64}, {"expected_url": ORIGIN + "/other"}]
)
def test_changed_page_or_request_aborts_before_action(browser_driver, changed):
    execute, requests, actions = browser_driver
    with pytest.raises(ValueError):
        execute(approved_payload(**changed))
    assert not actions and not any(r[0] == "POST" and r[2] == "allowed" for r in requests)


def test_stale_fixture_state_fails_closed(browser_driver):
    execute, requests, actions = browser_driver
    task = approved_payload()
    task["authorization"]["fixture_state"] = "a" * 64
    with pytest.raises(ValueError, match="state changed"):
        execute(task)
    assert not actions


def test_unapproved_actions_are_rejected_before_browser_start(browser_driver):
    execute, requests, actions = browser_driver
    with pytest.raises(ValueError, match="Human approval"):
        execute(payload(steps=[{"action": "click", "selector": "button"}]))
    assert not requests and not actions


@pytest.mark.parametrize("change", ["selector", "body", "origin", "fill_only"])
def test_unreviewed_authority_rejected(browser_driver, change):
    execute, requests, actions = browser_driver
    task = approved_payload()
    if change == "selector":
        task["steps"][1]["selector"] = "#delete"
    elif change == "body":
        task["authorization"]["body"] = "message=Changed"
    elif change == "origin":
        task["authorization"]["url"] = "https://example.com/"
    else:
        task["steps"].pop()
    with pytest.raises(ValueError):
        execute(task)
    assert not requests and not actions
