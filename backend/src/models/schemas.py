from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ─── Request Models ───────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CreateTeamRequest(BaseModel):
    name: str


class JoinTeamRequest(BaseModel):
    code: str


class CreateTokenRequest(BaseModel):
    label: str = Field(default="API token")


# ─── Auth Models ─────────────────────────────────────────────────────────────


class JwtPayload(BaseModel):
    """Decoded JWT token payload returned by the jwt_auth dependency."""

    model_config = ConfigDict(populate_by_name=True)

    sub: str
    email: str
    name: str
    tenant_id: str | None = Field(default=None, alias="tenantId")
    role: str | None = None
    iat: float
    exp: float


# ─── Response Models ──────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    email: str
    name: str
    tenant_id: str | None = Field(default=None, alias="tenantId")
    role: str | None = None


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


class MeResponse(BaseModel):
    """Response for the /auth/me endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(alias="userId")
    email: str
    name: str
    tenant_id: str | None = Field(default=None, alias="tenantId")
    role: str | None = None


class TeamResponse(BaseModel):
    id: str
    name: str
    slug: str


class TokenResponse(BaseModel):
    token: str
    label: str


class InviteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    expires_at: str = Field(alias="expiresAt")
    uses_remaining: int = Field(alias="usesRemaining")


class CreateInviteResponse(BaseModel):
    """Response for POST /teams/invite."""

    model_config = ConfigDict(populate_by_name=True)

    code: str
    expires_at: str = Field(alias="expiresAt")


class CreateTeamResponse(BaseModel):
    """Response for team creation."""

    model_config = ConfigDict(populate_by_name=True)

    token: str
    raw_api_token: str = Field(alias="rawApiToken")
    team: TeamResponse


class JoinTeamResponse(BaseModel):
    """Response for joining a team."""

    token: str
    team: TeamResponse


class TokenItemResponse(BaseModel):
    """Single API token in a list."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    created_at: str = Field(alias="createdAt")
    last_used_at: str | None = Field(default=None, alias="lastUsedAt")


class TokenListResponse(BaseModel):
    """Response for listing API tokens."""

    tokens: list[TokenItemResponse]


class CreateTokenResponse(BaseModel):
    """Response for creating a new API token."""

    model_config = ConfigDict(populate_by_name=True)

    token: str
    label: str
    created_at: str = Field(alias="createdAt")


class SessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId")
    title: str
    summary: str | None = None
    status: str
    run_count: int = Field(alias="runCount")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    last_run_at: str | None = Field(default=None, alias="lastRunAt")


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class GraphNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str
    status: str
    tags: list[str]
    supersedes: str | None = None
    superseded_by: str | None = Field(default=None, alias="supersededBy")
    updated_at: str = Field(alias="updatedAt")
    created_at: str = Field(alias="createdAt")
    connections: int = Field(default=0)


class GraphLink(BaseModel):
    source: str
    target: str
    type: Literal["related", "supersedes"]


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


# ─── Agent Event Types ────────────────────────────────────────────────────────

AgentEventType = Literal[
    "reasoning_checkpoint",
    "tool_call_started",
    "tool_call_completed",
    "subagent_invoked",
    "run_started",
    "run_completed",
    "final_response",
]


class AgentEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: AgentEventType
    author: str | None = None
    content: str | None = None
    sequence: int | None = None
    timestamp: str | None = None
    is_final: bool = Field(default=False, serialization_alias="isFinal")
