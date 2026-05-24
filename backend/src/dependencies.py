"""FastAPI dependency injection for auth and services."""

from __future__ import annotations

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.config import settings
from src.models.schemas import JWTPayload
from src.services.event_feed import AgentEventFeed
from src.services.tenant_resolver import TenantContext, TenantResolver

bearer_scheme = HTTPBearer()


async def get_db(request: Request) -> AsyncIOMotorDatabase:
    """Database dependency — available to all routes."""
    return request.app.state.mongo.db


async def get_event_feed(request: Request) -> AgentEventFeed:
    """Event feed dependency."""
    return request.app.state.event_feed


async def jwt_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> JWTPayload:
    """JWT auth dependency for frontend routes.

    Decodes the JWT and returns a validated JWTPayload model.
    Raises 401 on invalid or expired tokens.
    """
    try:
        payload: dict = pyjwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return JWTPayload.model_validate(payload)
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired JWT",
        ) from exc


async def api_token_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TenantContext:
    """API token auth dependency for harness routes.

    Resolves the bearer token to a TenantContext via SHA-256 lookup.
    Raises 401 if the token is invalid.
    """
    db = request.app.state.mongo.db
    resolver = TenantResolver(db)
    ctx = await resolver.resolve(credentials.credentials)
    if not ctx:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return ctx
