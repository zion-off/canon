from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.models.schemas._base import MongoModel


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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


class StreamTokenResponse(BaseModel):
    token: str
