from __future__ import annotations

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    session_id: str = Field(alias="sessionId")
    request: str
    context: str = ""
    title: str | None = None


class AgentRunResponse(BaseModel):
    model_config = {"populate_by_name": True}

    run_id: str = Field(alias="runId")
    session_id: str = Field(alias="sessionId")
    tenant_id: str = Field(alias="tenantId")


class AgentConfirmRequest(BaseModel):
    accepted: bool
    response: str | None = None


class AgentConfirmResponse(BaseModel):
    resolved: bool
