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
from src.models.documents import (
    ApiTokenDocument,
    InviteDocument,
    TenantDocument,
)
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

    tenant = TenantDocument.model_construct(
        name=body.name,
        slug=slug,
        embedding_model=settings.embedding_model,
        created_at=datetime.now(UTC),
        settings={"maxGraphDepth": 2},
    )
    await tenant.insert()
    tenant_id = tenant.id

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "tenantId": tenant_id,
                "role": "owner",
                "updatedAt": datetime.now(UTC),
            }
        },
    )

    # Generate default API token
    raw_token = f"ct_{secrets.token_urlsafe(32)}"
    await ApiTokenDocument.model_construct(
        tenant_id=tenant_id,
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        label="Default",
        created_at=datetime.now(UTC),
        last_used_at=None,
    ).insert()

    token = issue_jwt(user_id, user.email, user.name, str(tenant_id), "owner")

    return CreateTeamResponse(
        token=token,
        rawApiToken=raw_token,
        team=TeamResponse.model_validate(tenant.model_dump(by_alias=True)),
    )


@router.post("/join", response_model=JoinTeamResponse)
async def join_team(
    body: JoinTeamRequest,
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JoinTeamResponse:
    """Join an existing team via invite code."""
    now = datetime.now(UTC)

    invite = await InviteDocument.find_one({"code": body.code})
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invite code")
    if invite.expires_at < now:
        raise HTTPException(status_code=400, detail="Invite code has expired")
    if invite.uses_remaining <= 0:
        raise HTTPException(status_code=400, detail="Invite code has no remaining uses")

    tenant_id = invite.tenant_id
    user_id = user.sub

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"tenantId": tenant_id, "role": "member", "updatedAt": now}},
    )

    await db.invites.update_one(
        {"_id": invite.id},
        {"$inc": {"usesRemaining": -1}},
    )

    tenant = await TenantDocument.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Team not found")

    token = issue_jwt(user_id, user.email, user.name, str(tenant_id), "member")

    return JoinTeamResponse(
        token=token,
        team=TeamResponse.model_validate(tenant.model_dump(by_alias=True)),
    )


@router.post("/invite", response_model=CreateInviteResponse)
async def create_invite(
    user: JwtPayload = Depends(jwt_auth),
) -> CreateInviteResponse:
    """Create an invite code (owner only)."""
    if user.role != "owner":
        raise HTTPException(
            status_code=403, detail="Only team owners can create invites"
        )
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User does not belong to a team")

    now = datetime.now(UTC)
    code = secrets.token_hex(4)
    expires_at = now + timedelta(days=7)

    await InviteDocument.model_construct(
        tenant_id=ObjectId(user.tenant_id),
        code=code,
        created_by=ObjectId(user.sub),
        uses_remaining=10,
        expires_at=expires_at,
        created_at=now,
    ).insert()

    return CreateInviteResponse(code=code, expiresAt=expires_at.isoformat())


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
    tokens = [TokenItemResponse.model_validate(doc) async for doc in cursor]
    return TokenListResponse(tokens=tokens)


@router.post("/tokens", response_model=CreateTokenResponse)
async def create_token(
    body: CreateTokenRequest,
    user: JwtPayload = Depends(jwt_auth),
) -> CreateTokenResponse:
    """Create a new API token (owner only)."""
    if user.role != "owner":
        raise HTTPException(
            status_code=403, detail="Only team owners can create API tokens"
        )

    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User does not belong to a team")

    now = datetime.now(UTC)
    raw_token = f"ct_{secrets.token_urlsafe(32)}"

    await ApiTokenDocument.model_construct(
        tenant_id=ObjectId(user.tenant_id),
        user_id=user.sub,
        token_hash=_hash_token(raw_token),
        label=body.label,
        created_at=now,
        last_used_at=None,
    ).insert()

    return CreateTokenResponse(
        token=raw_token, label=body.label, createdAt=now.isoformat()
    )
