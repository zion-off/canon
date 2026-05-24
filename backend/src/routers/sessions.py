"""Session and event streaming routes for frontend (JWT) and harness (API token)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dependencies import api_token_auth, get_db, get_event_feed, jwt_auth
from src.models.schemas import AgentEvent, JwtPayload, SessionResponse
from src.services.event_feed import AgentEventFeed
from src.services.tenant_resolver import TenantContext

router = APIRouter(prefix="/sessions", tags=["sessions"])
harness_router = APIRouter(prefix="/tenants/{tenant_id}", tags=["harness-sessions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc_to_session(doc: dict[str, Any]) -> SessionResponse:
    """Convert a MongoDB session document to a SessionResponse model."""
    return SessionResponse(
        sessionId=doc["sessionId"],
        title=doc.get("title", ""),
        summary=doc.get("summary"),
        status=doc.get("status", ""),
        runCount=doc.get("runCount", 0),
        createdAt=str(doc.get("createdAt", "")),
        updatedAt=str(doc.get("updatedAt", "")),
        lastRunAt=doc["lastRunAt"].isoformat() if doc.get("lastRunAt") else None,
    )


def _doc_to_event(doc: dict[str, Any]) -> AgentEvent:
    """Convert a MongoDB event document to an AgentEvent model."""
    return AgentEvent(
        type=doc["type"],
        author=doc.get("author"),
        content=doc.get("content"),
        sequence=doc.get("sequence"),
        timestamp=str(doc.get("timestamp", "")) if doc.get("timestamp") else None,
        is_final=doc.get("isFinal", False),
    )


def _require_tenant_id(user: JwtPayload) -> str:
    """Extract tenantId from JWT payload, raising 400 if absent."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenantId")
    return user.tenant_id


def _validate_tenant_access(tenant_id: str, ctx: TenantContext) -> None:
    """Ensure the path tenant_id matches the token's tenant. Raises 403 on mismatch."""
    if tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")


async def _sse_stream(
    event_feed: AgentEventFeed,
    tenant_id: str,
    session_id: str,
    after_sequence: int,
) -> AsyncIterator[str]:
    """Shared SSE generator: replays stored events then streams live ones."""
    stored = await event_feed.replay(tenant_id, session_id, after_sequence)
    for evt in stored:
        event_id = evt.get("sequence", 0)
        yield f"id: {event_id}\ndata: {json.dumps(evt, default=str)}\n\n"

    async for evt in event_feed.subscribe(tenant_id, session_id):
        event_id = evt.get("sequence", 0)
        yield f"id: {event_id}\ndata: {json.dumps(evt, default=str)}\n\n"


# ---------------------------------------------------------------------------
# Frontend routes (JWT auth)
# ---------------------------------------------------------------------------


@router.get("")
async def list_sessions(
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[SessionResponse]:
    """List sessions for the authenticated user's tenant."""
    tenant_id = _require_tenant_id(user)
    cursor = (
        db.sessions.find({"tenantId": ObjectId(tenant_id)})
        .sort("lastRunAt", -1)
        .limit(20)
    )
    return [_doc_to_session(doc) async for doc in cursor]


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionResponse:
    """Get a single session by sessionId."""
    tenant_id = _require_tenant_id(user)
    doc = await db.sessions.find_one(
        {"sessionId": session_id, "tenantId": ObjectId(tenant_id)}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return _doc_to_session(doc)


@router.get("/{session_id}/events")
async def list_session_events(
    session_id: str,
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[AgentEvent]:
    """List all events for a session, ordered by sequence."""
    tenant_id = _require_tenant_id(user)
    cursor = db.agent_events.find(
        {"sessionId": session_id, "tenantId": ObjectId(tenant_id)}
    ).sort("sequence", 1)
    return [_doc_to_event(doc) async for doc in cursor]


@router.get("/{session_id}/stream")
async def stream_session_events(
    session_id: str,
    user: JwtPayload = Depends(jwt_auth),
    event_feed: AgentEventFeed = Depends(get_event_feed),
    last_event_id: int = Query(default=0),
) -> StreamingResponse:
    """SSE stream of session events."""
    tenant_id = _require_tenant_id(user)
    return StreamingResponse(
        _sse_stream(event_feed, tenant_id, session_id, last_event_id),
        media_type="text/event-stream",
    )


# ---------------------------------------------------------------------------
# Harness routes (API token auth)
# ---------------------------------------------------------------------------


@harness_router.get("/sessions")
async def harness_list_sessions(
    tenant_id: str,
    ctx: TenantContext = Depends(api_token_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[SessionResponse]:
    """List sessions for a tenant (harness access)."""
    _validate_tenant_access(tenant_id, ctx)
    cursor = (
        db.sessions.find({"tenantId": ObjectId(tenant_id)})
        .sort("lastRunAt", -1)
        .limit(20)
    )
    return [_doc_to_session(doc) async for doc in cursor]


@harness_router.get("/sessions/{session_id}/events")
async def harness_list_session_events(
    tenant_id: str,
    session_id: str,
    ctx: TenantContext = Depends(api_token_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[AgentEvent]:
    """List events for a session (harness access)."""
    _validate_tenant_access(tenant_id, ctx)
    cursor = db.agent_events.find(
        {"sessionId": session_id, "tenantId": ObjectId(tenant_id)}
    ).sort("sequence", 1)
    return [_doc_to_event(doc) async for doc in cursor]


@harness_router.get("/sessions/{session_id}/stream")
async def harness_stream_session_events(
    tenant_id: str,
    session_id: str,
    ctx: TenantContext = Depends(api_token_auth),
    event_feed: AgentEventFeed = Depends(get_event_feed),
    last_event_id: int = Query(default=0),
) -> StreamingResponse:
    """SSE stream of session events (harness access)."""
    _validate_tenant_access(tenant_id, ctx)
    return StreamingResponse(
        _sse_stream(event_feed, tenant_id, session_id, last_event_id),
        media_type="text/event-stream",
    )
