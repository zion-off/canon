"""Team management router: creation, joining, invites, and API tokens."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.config import settings
from src.dependencies import get_db, jwt_auth
from src.models.schemas import (
    CreateInviteResponse,
    CreateTeamRequest,
    CreateTeamResponse,
    CreateTokenRequest,
    CreateTokenResponse,
    JoinTeamRequest,
    JoinTeamResponse,
    JwtPayload,
    TeamResponse,
    TokenItemResponse,
    TokenListResponse,
)
from src.services.jwt import issue_jwt

router = APIRouter(prefix="/teams", tags=["teams"])


def _hash_token(raw: str) -> str:
    """Produce a hex-encoded SHA-256 hash of a raw API token."""
    return sha256(raw.encode()).hexdigest()


def _slugify(name: str) -> str:
    """Convert a team name to a URL-safe slug."""
    return name.strip().lower().replace(" ", "-")


@router.post("/create", response_model=CreateTeamResponse)
async def create_team(
    body: CreateTeamRequest,
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CreateTeamResponse:
    """Create a new team (tenant), assign caller as owner, issue default API token."""
    user_id = user.sub
    slug = _slugify(body.name)

    tenant = {
        "name": body.name,
        "slug": slug,
        "embeddingModel": settings.embedding_model,
        "createdAt": datetime.now(UTC),
        "settings": {"maxGraphDepth": 3},
    }
    result = await db.tenants.insert_one(tenant)
    tenant_id = result.inserted_id

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"tenantId": tenant_id, "role": "owner", "updatedAt": datetime.now(UTC)}},
    )

    # Generate default API token
    raw_token = f"ct_{secrets.token_urlsafe(32)}"
    await db.api_tokens.insert_one(
        {
            "tenantId": tenant_id,
            "userId": user_id,
            "tokenHash": _hash_token(raw_token),
            "label": "Default",
            "createdAt": datetime.now(UTC),
            "lastUsedAt": None,
        }
    )

    token = issue_jwt(user_id, user.email, user.name, str(tenant_id), "owner")

    return CreateTeamResponse(
        token=token,
        raw_api_token=raw_token,
        team=TeamResponse(id=str(tenant_id), name=body.name, slug=slug),
    )


@router.post("/join", response_model=JoinTeamResponse)
async def join_team(
    body: JoinTeamRequest,
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JoinTeamResponse:
    """Join an existing team via invite code."""
    now = datetime.now(UTC)

    invite = await db.invites.find_one({"code": body.code})
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invite code")
    if invite["expiresAt"] < now:
        raise HTTPException(status_code=400, detail="Invite code has expired")
    if invite["usesRemaining"] <= 0:
        raise HTTPException(status_code=400, detail="Invite code has no remaining uses")

    tenant_id = invite["tenantId"]
    user_id = user.sub

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"tenantId": tenant_id, "role": "member", "updatedAt": now}},
    )

    await db.invites.update_one(
        {"_id": invite["_id"]},
        {"$inc": {"usesRemaining": -1}},
    )

    tenant = await db.tenants.find_one({"_id": tenant_id})
    token = issue_jwt(user_id, user.email, user.name, str(tenant_id), "member")

    return JoinTeamResponse(
        token=token,
        team=TeamResponse(id=str(tenant_id), name=tenant["name"], slug=tenant["slug"]),
    )


@router.post("/invite", response_model=CreateInviteResponse)
async def create_invite(
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CreateInviteResponse:
    """Create an invite code (owner only)."""
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only team owners can create invites")

    now = datetime.now(UTC)
    code = secrets.token_hex(4)
    expires_at = now + timedelta(days=7)

    await db.invites.insert_one(
        {
            "tenantId": ObjectId(user.tenant_id),
            "code": code,
            "createdBy": ObjectId(user.sub),
            "usesRemaining": 10,
            "expiresAt": expires_at,
            "createdAt": now,
        }
    )

    return CreateInviteResponse(code=code, expires_at=expires_at.isoformat())


@router.get("/tokens", response_model=TokenListResponse)
async def list_tokens(
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenListResponse:
    """List all API tokens for the user's team."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User does not belong to a team")

    cursor = db.api_tokens.find(
        {"tenantId": ObjectId(user.tenant_id)},
        {"_id": 1, "label": 1, "createdAt": 1, "lastUsedAt": 1},
    )
    tokens: list[TokenItemResponse] = []
    async for doc in cursor:
        tokens.append(
            TokenItemResponse(
                id=str(doc["_id"]),
                label=doc["label"],
                created_at=doc["createdAt"].isoformat(),
                last_used_at=(
                    doc["lastUsedAt"].isoformat() if doc.get("lastUsedAt") else None
                ),
            )
        )

    return TokenListResponse(tokens=tokens)


@router.post("/tokens", response_model=CreateTokenResponse)
async def create_token(
    body: CreateTokenRequest,
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CreateTokenResponse:
    """Create a new API token (owner only)."""
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only team owners can create API tokens")

    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User does not belong to a team")

    now = datetime.now(UTC)
    raw_token = f"ct_{secrets.token_urlsafe(32)}"

    await db.api_tokens.insert_one(
        {
            "tenantId": ObjectId(user.tenant_id),
            "userId": user.sub,
            "tokenHash": _hash_token(raw_token),
            "label": body.label,
            "createdAt": now,
            "lastUsedAt": None,
        }
    )

    return CreateTokenResponse(
        token=raw_token, label=body.label, created_at=now.isoformat()
    )
