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
