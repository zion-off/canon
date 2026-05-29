"""Session and event streaming routes for the frontend (JWT auth)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.dependencies import (
    get_event_feed,
    jwt_auth,
    stream_auth,
)
from src.models.schemas import (
    AgentEvent,
    JwtPayload,
    SessionListResponse,
    SessionResponse,
    StreamTokenResponse,
)
from src.services.auth import AuthService
from src.services.event_feed import AgentEventFeed
from src.services.sessions import SessionService

router = APIRouter(tags=["sessions"])


def _jwt_tenant_id(user: JwtPayload) -> str:
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenantId")
    return user.tenant_id


@router.get("")
async def list_sessions(
    user: JwtPayload = Depends(jwt_auth),
    scope: str = Query(default="team"),
    limit: int = Query(default=20, ge=1, le=100),
    before: str | None = Query(default=None),
) -> SessionListResponse:
    tenant_id = _jwt_tenant_id(user)
    if scope == "me":
        return await SessionService.list_sessions(
            tenant_id, user_id=user.sub, limit=limit, before=before
        )
    return await SessionService.list_sessions(tenant_id, limit=limit, before=before)


@router.post("/stream/token", response_model=StreamTokenResponse)
async def create_sessions_stream_token(
    user: JwtPayload = Depends(jwt_auth),
) -> StreamTokenResponse:
    return StreamTokenResponse(token=AuthService.issue_stream_token(user))


@router.get("/stream")
async def stream_sessions(
    user: JwtPayload = Depends(stream_auth),
    event_feed: AgentEventFeed = Depends(get_event_feed),
) -> StreamingResponse:
    return StreamingResponse(
        SessionService.sessions_sse_stream(event_feed, _jwt_tenant_id(user)),
        media_type="text/event-stream",
    )


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: JwtPayload = Depends(jwt_auth),
) -> SessionResponse:
    session = await SessionService.get_session(_jwt_tenant_id(user), session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/events")
async def list_session_events(
    session_id: str,
    user: JwtPayload = Depends(jwt_auth),
) -> list[AgentEvent]:
    return await SessionService.list_events(_jwt_tenant_id(user), session_id)


@router.get("/{session_id}/stream")
async def stream_session_events(
    session_id: str,
    user: JwtPayload = Depends(stream_auth),
    event_feed: AgentEventFeed = Depends(get_event_feed),
    last_event_id: int = Query(default=0),
) -> StreamingResponse:
    return StreamingResponse(
        SessionService.session_sse_stream(
            event_feed, _jwt_tenant_id(user), session_id, last_event_id
        ),
        media_type="text/event-stream",
    )
