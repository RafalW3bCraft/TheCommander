import hashlib
import ipaddress
import json
import re
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, model_validator

from commander.contracts import Strict
from commander.errors import DomainError


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def domain_name(value):
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", value):
        raise ValueError("Use exact lowercase public DNS names")
    if "." not in value or ".." in value or value.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Use exact public DNS names")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    raise ValueError("IP literal destinations are denied")


def safe_url(value, domains):
    try:
        u = urlsplit(value)
        if (
            u.scheme != "https"
            or not u.hostname
            or u.hostname not in domains
            or u.username
            or u.password
            or u.port not in (None, 443)
            or "\\" in value
            or any(ord(c) < 33 or ord(c) == 127 for c in value)
        ):
            raise ValueError()
        domain_name(u.hostname)
    except ValueError:
        raise DomainError(
            "Only approved public HTTPS domains are allowed", 422, "destination_denied"
        ) from None
    return value


class TaskInput(Strict):
    project_id: UUID
    kind: Literal["code", "browser"]
    goal: str = Field(min_length=3, max_length=4000, pattern=r".*\S.*")
    url: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def valid(self):
        if self.kind == "browser" and not self.url:
            raise ValueError("Browser tasks require a starting URL")
        if self.kind == "code" and self.url:
            raise ValueError("Code tasks have no network access")
        return self


class BrowserStep(Strict):
    action: Literal["fill", "click"]
    selector: str = Field(min_length=1, max_length=300)
    value: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def valid(self):
        if self.action == "click" and self.value:
            raise ValueError("Clicks cannot contain a fill value")
        return self


class BrowserPlan(Strict):
    explanation: str = Field(min_length=1, max_length=2000)
    steps: list[BrowserStep] = Field(default_factory=list, max_length=8)


class CodePlan(Strict):
    explanation: str = Field(min_length=1, max_length=2000)
    code: str = Field(min_length=1, max_length=20000)


class Verification(Strict):
    verified: bool
    explanation: str = Field(min_length=1, max_length=2000)


class Decision(Strict):
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    approve: bool


def browser_policy(settings, url):
    """Authority comes from operator configuration, never page content or a model."""
    safe_url(url, settings.sandbox_browser_domains)
    fixture = getattr(settings, "sandbox_browser_fixture_origin", "").rstrip("/")
    if fixture:
        safe_url(fixture, settings.sandbox_browser_domains)
        parsed = urlsplit(fixture)
        if parsed.path or parsed.query or parsed.fragment:
            raise DomainError("Fixture policy must be an HTTPS origin", 503, "destination_denied")
    if fixture and url == fixture + "/fixture":
        return {"read_urls": [url], "fixture_origin": fixture}
    parsed = urlsplit(url)
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise DomainError("Only reviewed read routes are permitted", 422, "destination_denied")
    return {"read_urls": [url], "fixture_origin": ""}


def browser_authorization(settings, job, plan, evidence):
    """Compile the one supported controlled form into a human-reviewable request."""
    from urllib.parse import urlencode
    from uuid import uuid4

    policy = browser_policy(settings, job["url"])
    steps = plan.model_dump()["steps"]
    if (
        not policy["fixture_origin"]
        or len(steps) != 2
        or steps[0]["action"] != "fill"
        or steps[0]["selector"] != "#message"
        or steps[1] != {"action": "click", "selector": "#submit", "value": ""}
    ):
        raise DomainError(
            "Writes require the controlled fixture: fill #message then click #submit",
            422,
            "action_denied",
        )
    return {
        "owner_id": str(job["owner_id"]),
        "job_id": str(job["id"]),
        "operation_id": str(uuid4()),
        "method": "POST",
        "url": policy["fixture_origin"] + "/fixture/commit",
        "body": urlencode({"message": steps[0]["value"]}),
        "headers": {"content-type": "application/x-www-form-urlencoded"},
        "page_sha256": evidence["page_sha256"],
        "fixture_state": evidence["fixture_state"],
        "message_sha256": hashlib.sha256(steps[0]["value"].encode()).hexdigest(),
    }
