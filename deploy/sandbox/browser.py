"""Trusted Playwright driver; tasks contain data and selectors, never Python or JS."""

import base64
import hashlib
import json
import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def execute(task):
    domains = frozenset(task["domains"])
    allowed_write = bool(task.get("approved"))
    blocked = []
    actions_active = False

    def allowed(url):
        try:
            u = urlsplit(url)
            return (
                u.scheme == "https"
                and u.hostname in domains
                and u.port in (None, 443)
                and not u.username
                and not u.password
            )
        except ValueError:
            return False

    if not allowed(task["url"]):
        raise ValueError("Starting URL denied")
    if task.get("steps") and not allowed_write:
        raise ValueError("Human approval is required before actions")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            chromium_sandbox=True,
            proxy={"server": "http://egress:3128"},
            args=["--disable-dev-shm-usage", "--disable-quic", "--proxy-bypass-list=<-loopback>"],
        )
        context = browser.new_context(
            viewport={"width": 640, "height": 480}, service_workers="block", accept_downloads=False
        )

        def route(request_route):
            request = request_route.request
            if not allowed(request.url) or (
                request.method not in ("GET", "HEAD") and not actions_active
            ):
                if len(blocked) < 30:
                    blocked.append({"method": request.method, "url": request.url[:300]})
                request_route.abort()
            else:
                request_route.continue_()

        context.route("**/*", route)
        context.route_web_socket("**/*", lambda socket: socket.close())
        page = context.new_page()
        context.on("page", lambda opened: opened.close() if opened != page else None)
        page.on("dialog", lambda dialog: dialog.dismiss())
        page.on("download", lambda download: download.cancel())
        page.set_default_timeout(6000)
        page.goto(task["url"], wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(500)
        if not allowed(page.url):
            raise ValueError("Navigation escaped approved domains")
        initial_hash = hashlib.sha256(page.content().encode()).hexdigest()
        if allowed_write and (
            initial_hash != task["expected_page_sha256"] or page.url != task["expected_url"]
        ):
            raise ValueError("Page changed since approval; inspect a new task before acting")
        actions_active = allowed_write
        for step in task.get("steps", []):
            locator = page.locator(step["selector"])
            if locator.count() != 1:
                raise ValueError("Action selector must identify exactly one element")
            if step["action"] == "fill":
                locator.fill(step["value"])
            elif step["action"] == "click":
                locator.click()
            else:
                raise ValueError("Unsupported browser action")
        controls = page.locator("input, textarea, select, button, a[href]").evaluate_all("""els => els.slice(0, 40).map(e => ({
          tag: e.tagName.toLowerCase(), type: e.type || '', text: (e.innerText || e.getAttribute('aria-label') || '').slice(0, 120),
          selector: e.id ? '#' + CSS.escape(e.id) : e.name ? e.tagName.toLowerCase() + '[name=' + JSON.stringify(e.name) + ']' : null
        }))""")
        screenshot = page.screenshot(type="jpeg", quality=20, full_page=False, timeout=6000)
        if len(screenshot) > 18000:
            raise ValueError("Screenshot exceeded evidence budget")
        result = {
            "url": page.url[:2000],
            "title": page.title()[:300],
            "text": page.locator("body").inner_text()[:8000],
            "page_sha256": initial_hash,
            "screenshot_sha256": hashlib.sha256(screenshot).hexdigest(),
            "screenshot": base64.b64encode(screenshot).decode(),
            "blocked_requests": blocked,
            "actions_executed": len(task.get("steps", [])),
            "controls": controls,
        }
        browser.close()
        return result


if __name__ == "__main__":
    try:
        task = json.loads(sys.stdin.read(32000))
        print(json.dumps(execute(task)))
    except Exception:
        # Browser/vendor errors may contain page text and payloads. No traceback.
        print("Browser execution failed or page changed; no completion claimed", file=sys.stderr)
        sys.exit(1)
