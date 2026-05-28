"""FastAPI dependency injection for auth and services."""

from __future__ import annotations

import jwt as pyjwt
from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.asynchronous.database import AsyncDatabase

from src.config import settings
from src.models.schemas import JwtPayload
from src.services.event_feed import AgentEventFeed
from src.services.tenant_resolver import TenantContext, TenantResolver

required_bearer_scheme = HTTPBearer()


def _decode_jwt(token: str) -> JwtPayload:
    try:
        payload: dict = pyjwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return JwtPayload(**payload)
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        ) from exc


async def get_db(request: Request) -> AsyncDatabase:
    """Database dependency — available to all routes."""
    return request.app.state.mongo.db


async def get_event_feed(request: Request) -> AgentEventFeed:
    """Event feed dependency."""
    return request.app.state.event_feed


async def jwt_auth(
    credentials: HTTPAuthorizationCredentials = Depends(required_bearer_scheme),
) -> JwtPayload:
    """JWT auth dependency for frontend routes."""
    return _decode_jwt(credentials.credentials)


async def stream_auth(
    token: str | None = Query(default=None),
) -> JwtPayload:
    """Auth dependency for SSE endpoints — JWT passed as a query param.

    The token is a short-lived (2h) JWT signed with the same secret but
    issued specifically for stream access.  ``pyjwt.decode`` handles
    signature + expiry validation, so no DB lookup is needed.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing stream token")
    return _decode_jwt(token)


async def api_token_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(required_bearer_scheme),
) -> TenantContext:
    """API token auth dependency for harness routes.

    Resolves the bearer token to a TenantContext via SHA-256 lookup.
    Raises 401 if the token is invalid.
    """
    resolver = TenantResolver()
    ctx = await resolver.resolve(credentials.credentials)
    if not ctx:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return ctx
