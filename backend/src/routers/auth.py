from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import jwt_auth
from src.models.documents import UserDocument
from src.models.schemas import (
    JwtPayload,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    UserResponse,
)
from src.services.jwt import issue_jwt

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse)
async def register(
    body: RegisterRequest,
) -> LoginResponse:
    """Create account, return JWT. No auth required."""
    email = body.email.strip().lower()
    password_hash = (
        await asyncio.to_thread(bcrypt.hashpw, body.password.encode(), bcrypt.gensalt())
    ).decode()
    now = datetime.now(UTC)
    user = UserDocument.model_construct(
        email=email,
        name=body.name,
        password_hash=password_hash,
        tenant_id=None,
        role=None,
        created_at=now,
        updated_at=now,
    )
    try:
        await user.insert()
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(
                status_code=409, detail="Email already registered"
            ) from e
        raise
    token = issue_jwt(str(user.id), email, body.name, None, None)
    return LoginResponse(
        token=token,
        user=UserResponse.model_validate(user.model_dump(by_alias=True)),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
) -> LoginResponse:
    """Validate credentials, return JWT."""
    user = await UserDocument.find_one({"email": body.email.strip().lower()})
    if not user or not await asyncio.to_thread(
        bcrypt.checkpw, body.password.encode(), user.password_hash.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tenant_id = str(user.tenant_id) if user.tenant_id else None
    token = issue_jwt(
        str(user.id),
        user.email,
        user.name,
        tenant_id,
        user.role,
    )
    return LoginResponse(
        token=token,
        user=UserResponse.model_validate(user.model_dump(by_alias=True)),
    )


@router.get("/me", response_model=MeResponse)
async def me(user: JwtPayload = Depends(jwt_auth)) -> MeResponse:
    """Current user from JWT."""
    return MeResponse(
        userId=user.sub,
        email=user.email,
        name=user.name,
        tenantId=user.tenant_id,
        role=user.role,
    )
