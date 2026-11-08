from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    owner_id: UUID
    project_id: UUID | None = None


class RecordKey(Scope):
    id: UUID


class RevisionedKey(RecordKey):
    revision: int = Field(ge=1, strict=True)


class Record(RevisionedKey):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value


class Search(Scope):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20, strict=True)

    @field_validator("query")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Query must not be blank")
        return value
