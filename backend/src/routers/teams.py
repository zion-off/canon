"""Team management router: creation, joining, invites, and API tokens."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from src.config import settings
from src.constants import Role
from src.dependencies import jwt_auth
from src.models.documents import (
    ApiTokenDocument,
    InviteDocument,
    TenantDocument,
    UserDocument,
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
) -> CreateTeamResponse:
    """Create a new team (tenant), assign caller as owner, issue default API token."""
    if user.tenant_id:
        raise HTTPException(status_code=409, detail="User already belongs to a team")
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

    await UserDocument.find_one({"_id": ObjectId(user_id)}).set(
        {
            UserDocument.tenant_id: tenant_id,
            UserDocument.role: Role.OWNER,
            UserDocument.updated_at: datetime.now(UTC),
        }
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

    token = issue_jwt(user_id, user.email, user.name, str(tenant_id), Role.OWNER)

    return CreateTeamResponse(
        token=token,
        rawApiToken=raw_token,
        team=TeamResponse.model_validate(tenant.model_dump(by_alias=True)),
    )


@router.post("/join", response_model=JoinTeamResponse)
async def join_team(
    body: JoinTeamRequest,
    user: JwtPayload = Depends(jwt_auth),
) -> JoinTeamResponse:
    """Join an existing team via invite code."""
    if user.tenant_id:
        raise HTTPException(status_code=409, detail="User already belongs to a team")
    now = datetime.now(UTC)

    invite = await InviteDocument.find_one({"code": body.code})
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invite code")
    if invite.expires_at < now:
        raise HTTPException(status_code=400, detail="Invite code has expired")

    tenant_id = invite.tenant_id
    user_id = user.sub

    await UserDocument.find_one({"_id": ObjectId(user_id)}).set(
        {
            UserDocument.tenant_id: tenant_id,
            UserDocument.role: Role.MEMBER,
            UserDocument.updated_at: now,
        }
    )

    # Atomic conditional decrement — prevents overbooking under concurrency
    result = await InviteDocument.find_one(
        InviteDocument.id == invite.id,
        InviteDocument.uses_remaining > 0,
    ).inc({InviteDocument.uses_remaining: -1})
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Invite code has no remaining uses")

    tenant = await TenantDocument.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Team not found")

    token = issue_jwt(user_id, user.email, user.name, str(tenant_id), Role.MEMBER)

    return JoinTeamResponse(
        token=token,
        team=TeamResponse.model_validate(tenant.model_dump(by_alias=True)),
    )


@router.post("/invite", response_model=CreateInviteResponse)
async def create_invite(
    user: JwtPayload = Depends(jwt_auth),
) -> CreateInviteResponse:
    """Create an invite code (owner only)."""
    if user.role != Role.OWNER:
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
) -> TokenListResponse:
    """List all API tokens for the user's team."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User does not belong to a team")

    cursor = ApiTokenDocument.find(
        ApiTokenDocument.tenant_id == ObjectId(user.tenant_id),
    )
    tokens = []
    async for doc in cursor:
        tokens.append(TokenItemResponse.model_validate(doc.model_dump(by_alias=True)))
    return TokenListResponse(tokens=tokens)


@router.post("/tokens", response_model=CreateTokenResponse)
async def create_token(
    body: CreateTokenRequest,
    user: JwtPayload = Depends(jwt_auth),
) -> CreateTokenResponse:
    """Create a new API token (owner only)."""
    if user.role != Role.OWNER:
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
