from datetime import datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Strict):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=256)


class Bootstrap(Login):
    token: str = Field(min_length=32, max_length=200)


class MemoryInput(Strict):
    kind: Literal["explicit", "inferred", "episodic", "task", "evidence", "procedural"] = "explicit"
    key: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    expires_at: datetime | None = None


class MemoryEdit(MemoryInput):
    revision: int = Field(ge=1)


class ConnectionInput(Strict):
    secret: str = Field(default="", max_length=4096)
    repository: str = Field(default="", pattern=r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?$")
    domains: list[str] = Field(default_factory=list, max_length=10)
    enabled: bool = True
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def expiry_aware(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("Credential expiry must include a UTC offset")
        return value

    @field_validator("domains")
    @classmethod
    def domains_valid(cls, values):
        import re

        if any(not re.fullmatch(r"[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+", v) for v in values):
            raise ValueError("Use domain names only")
        return values


SkillName = Literal["conversation", "engineering-briefing", "research-to-action", "follow-through"]


class RunInput(Strict):
    skill: SkillName = "conversation"
    prompt: str = Field(min_length=1, max_length=8000)
    conversation_id: UUID | None = None


class ScheduleInput(Strict):
    skill: SkillName = "follow-through"
    prompt: str = Field(min_length=1, max_length=8000)
    next_at: datetime
    timezone: str = "UTC"
    interval_seconds: int | None = Field(default=None, ge=60, le=31536000)
    paused: bool = False

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid IANA timezone") from None
        return value

    @field_validator("next_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("Execution time must include a UTC offset")
        return value


class ScheduleEdit(ScheduleInput):
    revision: int = Field(ge=1)


class Issue(Strict):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=12000)


class Approval(Strict):
    args_hash: str = Field(min_length=64, max_length=64)


class Note(Strict):
    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.md$")
    content: str = Field(min_length=1, max_length=20000)


class Search(Strict):
    query: str = Field(min_length=1, max_length=500)


class Empty(Strict):
    pass


# Response contracts are the source for generated TypeScript types.
class UserView(BaseModel):
    owner_id: str
    username: str
    csrf: str


class MemoryView(BaseModel):
    id: UUID
    kind: str
    key: str
    content: str
    source: str
    sensitivity: str
    observed_at: datetime
    updated_at: datetime
    revision: int
    expires_at: datetime | None


class RunView(BaseModel):
    id: UUID
    skill: str
    prompt: str
    status: str
    result: str | None
    error: str | None
    created_at: datetime
    conversation_id: UUID | None
    schedule_id: UUID | None
    skill_version: str


class IssueArguments(Issue):
    correlation_marker: str
    repository: str


class ReceiptView(BaseModel):
    url: str
    verified_at: str
    provider: str
    number: int


class ActionView(BaseModel):
    id: UUID
    tool: str
    status: str
    arguments: IssueArguments
    args_hash: str
    expires_at: datetime
    receipt: ReceiptView | None
    error: str | None


class EvidenceView(BaseModel):
    id: UUID
    url: str
    title: str
    excerpt: str
    fetched_at: datetime


class EventView(BaseModel):
    id: int
    kind: str
    created_at: datetime
    payload: dict


class RunDetailView(RunView):
    events: list[EventView]
    actions: list[ActionView]
    evidence: list[EvidenceView]


class ConnectionConfigView(BaseModel):
    expires_at: datetime | None = None
    repository: str | None = None
    domains: list[str] | None = None
    enabled: bool | None = None
    model: str | None = None
    endpoint: str | None = None


class ConnectionView(BaseModel):
    kind: str
    status: str
    revision: int
    validated_at: datetime | None
    detail: str | None
    config: ConnectionConfigView


class ScheduleView(BaseModel):
    id: UUID
    skill: str
    prompt: str
    timezone: str
    next_at: datetime | None
    interval_seconds: int | None
    paused: bool
    revision: int
    last_at: datetime | None


class SkillView(BaseModel):
    id: str
    name: str
    purpose: str
    version: str
    tools: list[str]
    example: str
    hash: str
    input_schema: dict
    output_schema: dict
    source_restrictions: str
    max_steps: int
    max_seconds: int


class ConversationView(BaseModel):
    id: UUID
    title: str
    created_at: datetime


class MessageView(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ErrorField(BaseModel):
    field: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[ErrorField] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
