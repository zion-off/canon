from __future__ import annotations

from pydantic import BaseModel, Field

from src.models.schemas._base import MongoModel


class SessionResponse(MongoModel):
    session_id: str = Field(alias="sessionId")
    tenant_id: str = Field(default="", alias="tenantId")
    user_id: str = Field(default="", alias="userId")
    title: str = Field(default="")
    summary: str | None = None
    run_count: int = Field(default=0, alias="runCount")
    created_at: str = Field(default="", alias="createdAt")
    updated_at: str = Field(default="", alias="updatedAt")
    last_run_at: str | None = Field(default=None, alias="lastRunAt")


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    next_cursor: str | None = Field(default=None, alias="nextCursor")
