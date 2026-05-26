"""Session and event streaming routes for frontend (JWT) and harness (API token)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.dependencies import api_token_auth, get_event_feed, jwt_auth
from src.models.documents import AgentEventDocument, SessionDocument
from src.models.schemas import AgentEvent, JwtPayload, SessionResponse
from src.services.event_feed import AgentEventFeed
from src.services.tenant_resolver import TenantContext

router = APIRouter(prefix="/sessions", tags=["sessions"])
harness_router = APIRouter(prefix="/tenants/{tenant_id}", tags=["harness-sessions"])


# ---------------------------------------------------------------------------
# Shared business logic (auth-agnostic — callers provide the resolved tenant_id)
# ---------------------------------------------------------------------------


async def _list_sessions(tenant_id: str) -> list[SessionResponse]:
    tenant_oid = ObjectId(tenant_id)
    sessions = (
        await SessionDocument.find(SessionDocument.tenant_id == tenant_oid)
        .sort("-lastRunAt")
        .limit(20)
        .to_list()
    )
    return [
        SessionResponse.model_validate(s.model_dump(by_alias=True)) for s in sessions
    ]


async def _list_events(tenant_id: str, session_id: str) -> list[AgentEvent]:
    tenant_oid = ObjectId(tenant_id)
    events = (
        await AgentEventDocument.find(
            AgentEventDocument.session_id == session_id,
            AgentEventDocument.tenant_id == tenant_oid,
        )
        .sort("sequence")
        .to_list()
    )
    return [AgentEvent.model_validate(e.model_dump(by_alias=True)) for e in events]


async def _sse_stream(
    event_feed: AgentEventFeed,
    tenant_id: str,
    session_id: str,
    after_sequence: int,
) -> AsyncIterator[str]:
    stored = await event_feed.replay(tenant_id, session_id, after_sequence)
    for evt in stored:
        yield f"id: {evt.sequence}\ndata: {evt.model_dump_json(by_alias=True)}\n\n"

    async for evt in event_feed.subscribe(tenant_id, session_id):
        yield f"id: {evt.sequence}\ndata: {evt.model_dump_json(by_alias=True)}\n\n"


def _stream_response(
    event_feed: AgentEventFeed,
    tenant_id: str,
    session_id: str,
    last_event_id: int,
) -> StreamingResponse:
    return StreamingResponse(
        _sse_stream(event_feed, tenant_id, session_id, last_event_id),
        media_type="text/event-stream",
    )


# ---------------------------------------------------------------------------
# Auth extraction helpers
# ---------------------------------------------------------------------------


def _jwt_tenant_id(user: JwtPayload) -> str:
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenantId")
    return user.tenant_id


def _check_tenant_match(path_tenant_id: str, ctx: TenantContext) -> None:
    if path_tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")


# ---------------------------------------------------------------------------
# Frontend routes (JWT auth)
# ---------------------------------------------------------------------------


@router.get("")
async def list_sessions(
    user: JwtPayload = Depends(jwt_auth),
) -> list[SessionResponse]:
    return await _list_sessions(_jwt_tenant_id(user))


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: JwtPayload = Depends(jwt_auth),
) -> SessionResponse:
    tenant_oid = ObjectId(_jwt_tenant_id(user))
    session = await SessionDocument.find_one(
        SessionDocument.session_id == session_id,
        SessionDocument.tenant_id == tenant_oid,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.model_validate(session.model_dump(by_alias=True))


@router.get("/{session_id}/events")
async def list_session_events(
    session_id: str,
    user: JwtPayload = Depends(jwt_auth),
) -> list[AgentEvent]:
    return await _list_events(_jwt_tenant_id(user), session_id)


@router.get("/{session_id}/stream")
async def stream_session_events(
    session_id: str,
    user: JwtPayload = Depends(jwt_auth),
    event_feed: AgentEventFeed = Depends(get_event_feed),
    last_event_id: int = Query(default=0),
) -> StreamingResponse:
    return _stream_response(event_feed, _jwt_tenant_id(user), session_id, last_event_id)


# ---------------------------------------------------------------------------
# Harness routes (API token auth)
# ---------------------------------------------------------------------------


@harness_router.get("/sessions")
async def harness_list_sessions(
    tenant_id: str,
    ctx: TenantContext = Depends(api_token_auth),
) -> list[SessionResponse]:
    _check_tenant_match(tenant_id, ctx)
    return await _list_sessions(tenant_id)


@harness_router.get("/sessions/{session_id}/events")
async def harness_list_session_events(
    session_id: str,
    tenant_id: str,
    ctx: TenantContext = Depends(api_token_auth),
) -> list[AgentEvent]:
    _check_tenant_match(tenant_id, ctx)
    return await _list_events(tenant_id, session_id)


@harness_router.get("/sessions/{session_id}/stream")
async def harness_stream_session_events(
    tenant_id: str,
    session_id: str,
    ctx: TenantContext = Depends(api_token_auth),
    event_feed: AgentEventFeed = Depends(get_event_feed),
    last_event_id: int = Query(default=0),
) -> StreamingResponse:
    _check_tenant_match(tenant_id, ctx)
    return _stream_response(event_feed, tenant_id, session_id, last_event_id)
