from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.models.schemas._base import MongoModel


class CreateTeamRequest(BaseModel):
    name: str


class JoinTeamRequest(BaseModel):
    code: str


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


class CreateTokenRequest(BaseModel):
    label: str = Field(default="API token")


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
