"""Trusted driver boundaries with a controlled Playwright double; no live browser."""

import hashlib
import importlib.util
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def browser_driver(monkeypatch):
    requests = []
    actions = []

    class Route:
        def __init__(self, method):
            self.request = SimpleNamespace(url="https://example.com/", method=method)

        def abort(self):
            requests.append((self.request.method, "denied"))

        def continue_(self):
            requests.append((self.request.method, "allowed"))

    class Locator:
        def count(self):
            return 1

        def fill(self, value):
            actions.append(("fill", value))
            context.handler(Route("POST"))

        def click(self):
            actions.append(("click", None))

        def evaluate_all(self, script):
            return []

        def inner_text(self):
            return "Controlled page"

    class Page:
        url = "https://example.com/"

        def on(self, *args):
            pass

        def set_default_timeout(self, value):
            pass

        def goto(self, *args, **kwargs):
            context.handler(Route("POST"))
            context.handler(Route("GET"))

        def wait_for_timeout(self, value):
            pass

        def content(self):
            return "controlled-page-html"

        def locator(self, selector):
            return Locator()

        def screenshot(self, **kwargs):
            return b"\xff\xd8\xffcontrolled-fixture"

        def title(self):
            return "Controlled"

    class Context:
        def route(self, pattern, handler):
            self.handler = handler

        def route_web_socket(self, *args):
            pass

        def new_page(self):
            return Page()

        def on(self, *args):
            pass

    context = Context()

    class Browser:
        def new_context(self, **kw):
            assert kw["service_workers"] == "block" and not kw["accept_downloads"]
            return context

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
    return module, requests, actions


def payload(**overrides):
    return {
        "url": "https://example.com/",
        "domains": ["example.com"],
        "approved": False,
        "steps": [],
        "expected_page_sha256": hashlib.sha256(b"controlled-page-html").hexdigest(),
        "expected_url": "https://example.com/",
        **overrides,
    }


def test_observation_has_no_actions_and_blocks_post(browser_driver):
    driver, requests, actions = browser_driver
    result = driver.execute(payload())
    assert not actions and result["actions_executed"] == 0
    assert ("POST", "denied") in requests and ("GET", "allowed") in requests
    assert (
        result["screenshot_sha256"] == hashlib.sha256(b"\xff\xd8\xffcontrolled-fixture").hexdigest()
    )


def test_approved_load_still_blocks_writes_until_page_check(browser_driver):
    driver, requests, actions = browser_driver
    driver.execute(
        payload(approved=True, steps=[{"action": "fill", "selector": "#name", "value": "Demo"}])
    )
    assert requests == [("POST", "denied"), ("GET", "allowed"), ("POST", "allowed")]
    assert actions == [("fill", "Demo")]


@pytest.mark.parametrize(
    "changed", [{"expected_page_sha256": "a" * 64}, {"expected_url": "https://example.com/other"}]
)
def test_changed_page_or_redirect_aborts_before_any_action(browser_driver, changed):
    driver, requests, actions = browser_driver
    with pytest.raises(ValueError, match="Page changed"):
        driver.execute(
            payload(approved=True, steps=[{"action": "click", "selector": "button"}], **changed)
        )
    assert not actions and ("POST", "allowed") not in requests


def test_unapproved_actions_are_rejected_before_browser_start(browser_driver):
    driver, requests, actions = browser_driver
    with pytest.raises(ValueError, match="Human approval"):
        driver.execute(payload(steps=[{"action": "click", "selector": "button"}]))
    assert not requests and not actions
