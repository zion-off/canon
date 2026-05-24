from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dependencies import get_db, jwt_auth
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
    body: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)
) -> LoginResponse:
    """Create account, return JWT. No auth required."""
    email = body.email.strip().lower()
    password_hash = (
        await asyncio.to_thread(bcrypt.hashpw, body.password.encode(), bcrypt.gensalt())
    ).decode()
    now = datetime.now(UTC)
    user = {
        "email": email,
        "name": body.name,
        "passwordHash": password_hash,
        "tenantId": None,
        "role": None,
        "createdAt": now,
        "updatedAt": now,
    }
    try:
        result = await db.users.insert_one(user)
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail="Email already registered") from e
        raise
    token = issue_jwt(str(result.inserted_id), email, body.name, None, None)
    return LoginResponse(
        token=token,
        user=UserResponse(
            id=str(result.inserted_id),
            email=email,
            name=body.name,
            tenantId=None,
            role=None,
        ),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)
) -> LoginResponse:
    """Validate credentials, return JWT."""
    user = await db.users.find_one({"email": body.email.strip().lower()})
    if not user or not await asyncio.to_thread(
        bcrypt.checkpw, body.password.encode(), user["passwordHash"].encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tenant_id = str(user["tenantId"]) if user.get("tenantId") else None
    token = issue_jwt(
        str(user["_id"]),
        user["email"],
        user["name"],
        tenant_id,
        user.get("role"),
    )
    return LoginResponse(
        token=token,
        user=UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            tenantId=tenant_id,
            role=user.get("role"),
        ),
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
