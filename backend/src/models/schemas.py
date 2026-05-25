from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

# ─── Base Model ──────────────────────────────────────────────────────────────


class MongoModel(BaseModel):
    """Base model for Pydantic schemas populated from MongoDB documents.

    Coerces ``ObjectId`` → ``str`` and ``datetime`` → ISO strings, and ignores
    extra fields so that ``model_validate(doc)`` works directly on a
    MongoDB cursor result.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _coerce_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, datetime):
                    data[k] = v.isoformat()
                elif isinstance(v, ObjectId):
                    data[k] = str(v)
        return data


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


class UserResponse(MongoModel):
    id: str = Field(validation_alias="_id")
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


class TeamResponse(MongoModel):
    id: str = Field(validation_alias="_id")
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


class TokenItemResponse(MongoModel):
    """Single API token in a list."""

    id: str = Field(validation_alias="_id")
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


class SessionResponse(MongoModel):
    session_id: str = Field(alias="sessionId")
    title: str = Field(default="")
    summary: str | None = None
    status: str = Field(default="")
    run_count: int = Field(default=0, alias="runCount")
    created_at: str = Field(default="", alias="createdAt")
    updated_at: str = Field(default="", alias="updatedAt")
    last_run_at: str | None = Field(default=None, alias="lastRunAt")


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class GraphNode(MongoModel):
    id: str = Field(validation_alias="_id")
    name: str
    description: str = Field(default="")
    status: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    supersedes: str | None = None
    superseded_by: str | None = Field(default=None, alias="supersededBy")
    updated_at: str = Field(default="", alias="updatedAt")
    created_at: str = Field(default="", alias="createdAt")
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


class AgentEvent(MongoModel):
    type: AgentEventType
    author: str | None = None
    content: str | None = None
    sequence: int | None = None
    timestamp: str | None = None
    is_final: bool = Field(
        default=False, validation_alias="isFinal", serialization_alias="isFinal"
    )
