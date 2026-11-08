"""Trusted driver: exact reviewed reads and one controlled-fixture write capability."""

import base64
import hashlib
import json
import sys
from urllib.parse import urlencode, urlsplit
from uuid import UUID

from playwright.sync_api import sync_playwright


def execute(task):
    domains = frozenset(task["domains"])
    approved = bool(task.get("approved"))
    blocked = []
    armed = False
    sent = False
    steps = task.get("steps", [])
    authority = task.get("authorization")
    policy = task.get("policy", {"read_urls": [task["url"]], "fixture_origin": ""})

    def allowed(url):
        try:
            u = urlsplit(url)
            return (
                u.scheme == "https"
                and u.hostname in domains
                and u.port in (None, 443)
                and not u.username
                and not u.password
                and "\\" not in url
                and not any(ord(c) < 33 or ord(c) == 127 for c in url)
            )
        except ValueError:
            return False

    if not allowed(task["url"]):
        raise ValueError("Starting URL denied")
    fixture = policy.get("fixture_origin", "")
    if policy.get("read_urls") != [task["url"]] or (
        fixture and task["url"] != fixture + "/fixture"
    ):
        raise ValueError("Invalid reviewed read policy")
    if not fixture:
        u = urlsplit(task["url"])
        if u.path not in ("", "/") or u.query or u.fragment:
            raise ValueError("Unreviewed read route")
    if steps and not approved:
        raise ValueError("Human approval is required before actions")
    if approved:
        if not fixture or not authority or len(steps) != 2:
            raise ValueError("Controlled fixture authorization required")
        if (
            steps[0]["action"] != "fill"
            or steps[0]["selector"] != "#message"
            or steps[1] != {"action": "click", "selector": "#submit", "value": ""}
            or authority["method"] != "POST"
            or authority["url"] != fixture + "/fixture/commit"
            or authority["body"] != urlencode({"message": steps[0]["value"]})
            or authority["headers"] != {"content-type": "application/x-www-form-urlencoded"}
            or authority["page_sha256"] != task["expected_page_sha256"]
        ):
            raise ValueError("Action manifest changed")
        UUID(authority["operation_id"])
    read_urls = frozenset(policy["read_urls"])
    status_url = fixture + "/fixture/state/" + authority["operation_id"] if approved else None
    write_receipt = None
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
            nonlocal sent, armed
            request = request_route.request
            # No redirects, child frames, external resources, prefetches or arbitrary GET routes.
            document = request.resource_type == "document" and request.frame == page.main_frame
            redirected = request.redirected_from is not None
            read = request.method == "GET" and (
                request.url in read_urls or (sent and request.url == status_url)
            )
            write = (
                armed
                and not sent
                and request.method == authority["method"]
                and request.url == authority["url"]
                and request.post_data == authority["body"]
                and request.headers.get("content-type") == authority["headers"]["content-type"]
            ) if approved else False
            if not allowed(request.url) or not document or redirected or not (read or write):
                if len(blocked) < 30:
                    # Never persist denied request bodies, query strings or credentials.
                    parsed = urlsplit(request.url)
                    blocked.append({"method": request.method, "target": parsed.hostname})
                request_route.abort()
            elif write:
                # Consume before continuation: retries and background duplicate writes are denied.
                sent = True
                armed = False
                headers = dict(request.headers)
                headers.update({
                    "x-commander-operation-id": authority["operation_id"],
                    "if-match": authority["fixture_state"],
                })
                request_route.continue_(headers=headers)
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
        if page.url != task["url"]:
            raise ValueError("Navigation escaped reviewed route")
        initial_hash = hashlib.sha256(page.content().encode()).hexdigest()
        if approved and (
            initial_hash != task["expected_page_sha256"] or page.url != task["expected_url"]
        ):
            raise ValueError("Page changed since approval; inspect a new task before acting")
        fixture_state = page.locator("#revision").inner_text() if fixture else None
        if approved and fixture_state != authority["fixture_state"]:
            raise ValueError("Fixture state changed since approval")
        for step in steps:
            locator = page.locator(step["selector"])
            if locator.count() != 1:
                raise ValueError("Action selector must identify exactly one element")
            if step["action"] == "fill":
                locator.fill(step["value"])
            else:
                armed = True
                locator.click()
                armed = False
        if approved:
            if not sent:
                raise ValueError("Approved request was not observed; no completion claimed")
            # Reconcile independently against the fixture's committed operation record.
            page.goto(status_url, wait_until="domcontentloaded", timeout=15000)
            write_receipt = json.loads(page.locator("#receipt").inner_text())
            if (
                write_receipt.get("operation_id") != authority["operation_id"]
                or write_receipt.get("status") != "committed"
                or write_receipt.get("writes") != 1
                or write_receipt.get("message_sha256") != authority["message_sha256"]
            ):
                raise ValueError("Write outcome uncertain; reconcile before another action")
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
            "actions_executed": len(steps),
            "write_receipt": write_receipt,
            "fixture_state": fixture_state,
            "controls": controls,
        }
        browser.close()
        return result


if __name__ == "__main__":
    try:
        task = json.loads(sys.stdin.read(32000))
        print(json.dumps(execute(task)))
    except Exception:
        print("Browser execution failed or page changed; no completion claimed", file=sys.stderr)
        sys.exit(1)
