"""Session and event stream business logic."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime

from bson import ObjectId

from src.models.documents import AgentEventDocument, SessionDocument
from src.models.schemas import (
    AgentEvent,
    AgentEventBase,
    SessionListResponse,
    SessionResponse,
)
from src.services.event_feed import AgentEventFeed


class SessionService:
    """Database queries and SSE stream generators for sessions and events."""

    @staticmethod
    async def get_session(tenant_id: str, session_id: str) -> SessionResponse | None:
        """Return a single session by ID, or None if not found or not owned by tenant."""
        tenant_oid = ObjectId(tenant_id)
        session = await SessionDocument.find_one(
            SessionDocument.session_id == session_id,
            SessionDocument.tenant_id == tenant_oid,
        )
        if not session:
            return None
        return SessionResponse.model_validate(session.model_dump(by_alias=True))

    @staticmethod
    async def list_sessions(
        tenant_id: str,
        *,
        user_id: str | None = None,
        limit: int = 20,
        before: str | None = None,
    ) -> SessionListResponse:
        """Return paginated sessions for a tenant, sorted by lastRunAt descending.

        Pass the returned nextCursor as `before` on the next call to fetch the next page.
        """
        tenant_oid = ObjectId(tenant_id)
        base: list = [SessionDocument.tenant_id == tenant_oid]
        if user_id:
            base.append(SessionDocument.user_id == user_id)

        page = list(base)
        if before:
            page.append({"lastRunAt": {"$lt": datetime.fromisoformat(before)}})

        total, sessions = await asyncio.gather(
            SessionDocument.find(*base).count(),
            SessionDocument.find(*page).sort("-lastRunAt").limit(limit).to_list(),
        )
        items = [SessionResponse.model_validate(s.model_dump(by_alias=True)) for s in sessions]
        next_cursor = items[-1].last_run_at if len(items) == limit else None
        return SessionListResponse(sessions=items, total=total, nextCursor=next_cursor)

    @staticmethod
    async def list_events(tenant_id: str, session_id: str) -> list[AgentEvent]:
        """Return all stored events for a session, ordered by sequence number."""
        tenant_oid = ObjectId(tenant_id)
        events = (
            await AgentEventDocument.find(
                AgentEventDocument.session_id == session_id,
                AgentEventDocument.tenant_id == tenant_oid,
            )
            .sort("sequence")
            .to_list()
        )
        return [
            AgentEventBase.from_document(
                e.model_dump(by_alias=True, exclude={"tenant_id", "id"})
            )
            for e in events
        ]

    @staticmethod
    async def session_sse_stream(
        event_feed: AgentEventFeed,
        tenant_id: str,
        session_id: str,
        after_sequence: int,
    ) -> AsyncIterator[str]:
        """Yield SSE-formatted events for a session, replaying history then streaming live."""
        stored = await event_feed.replay(tenant_id, session_id, after_sequence)
        for evt in stored:
            yield f"id: {evt.sequence}\ndata: {evt.model_dump_json(by_alias=True)}\n\n"

        async for evt in event_feed.subscribe(tenant_id, session_id):
            yield f"id: {evt.sequence}\ndata: {evt.model_dump_json(by_alias=True)}\n\n"

    @staticmethod
    async def sessions_sse_stream(
        event_feed: AgentEventFeed,
        tenant_id: str,
    ) -> AsyncIterator[str]:
        """Yield SSE-formatted session updates for a tenant (dashboard live list)."""
        async for session in event_feed.subscribe_sessions(tenant_id):
            yield f"data: {session.model_dump_json(by_alias=True)}\n\n"
