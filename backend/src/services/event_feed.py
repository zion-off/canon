"""Agent event feed for real-time streaming and persistence."""

from __future__ import annotations

import logging
from asyncio import Event, Lock, Queue
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bson import ObjectId

from src.models.documents import AgentEventDocument
from src.models.schemas import AgentEvent, AgentEventBase, SessionResponse


@dataclass
class PendingConfirmation:
    confirmation_id: str
    accepted: bool | None = None
    response: str | None = None
    resolved: Event = field(default_factory=Event)


class _FeedState:
    """Module-level singleton container for the AgentEventFeed."""

    instance: AgentEventFeed | None = None


def init_feed(feed: AgentEventFeed) -> None:
    """Initialize the global feed instance — called once during application startup."""
    _FeedState.instance = feed


def get_feed() -> AgentEventFeed:
    """Return the singleton AgentEventFeed. Raises if not yet initialized."""
    if _FeedState.instance is None:
        raise RuntimeError("AgentEventFeed not initialized")
    return _FeedState.instance


class AgentEventFeed:
    """Manages live event streaming and persistence for the Reasoning Feed.

    Assigns sequence numbers and timestamps centrally — callers provide
    type, author, content, and isFinal. This ensures globally ordered events
    regardless of whether they originate from the ReasoningFeedPlugin or the
    runner event loop.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Queue[AgentEvent]]] = {}
        self._sequences: dict[str, int] = {}  # session_id → current sequence
        self._locks: dict[str, Lock] = {}  # session_id → sequence lock
        self._session_subscribers: dict[str, list[Queue[SessionResponse]]] = {}
        self._pending_confirmations: dict[str, PendingConfirmation] = {}
        self._confirm_lock = Lock()

    async def broadcast(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        run_id: str,
        event: AgentEvent,
    ) -> None:
        """Broadcast an event to subscribers and persist to agent_events.

        Assigns sequence number and timestamp if not already present.
        """
        # Assign sequence (monotonically increasing per session, atomic)
        lock = self._locks.get(session_id)
        if lock is None:
            lock = Lock()
            self._locks[session_id] = lock
        async with lock:
            seq = self._sequences.get(session_id, 0) + 1
            self._sequences[session_id] = seq
            if event.sequence is None:
                event.sequence = seq
        now = datetime.now(UTC)
        if event.timestamp is None:
            event.timestamp = now.isoformat()
        if event.run_id is None:
            event.run_id = run_id

        # Serialize to dict for persistence
        event_dict = event.model_dump()

        # Persist for replay; run_id flows in via event_dict
        doc = AgentEventDocument.model_construct(
            tenant_id=ObjectId(tenant_id),
            user_id=user_id,
            session_id=session_id,
            created_at=now,
            **event_dict,
        )
        await doc.insert()

        # Fan out AgentEvent objects to live subscribers
        key = f"{tenant_id}:{session_id}"
        subscribers = self._subscribers.get(key, [])
        logging.getLogger(__name__).debug(
            "event_feed: broadcast | key=%s seq=%d type=%s subscribers=%d",
            key,
            seq,
            event.type,
            len(subscribers),
        )
        for queue in subscribers:
            await queue.put(event)

    async def subscribe(
        self, tenant_id: str, session_id: str
    ) -> AsyncIterator[AgentEvent]:
        """Subscribe to live events for a session."""
        key = f"{tenant_id}:{session_id}"
        queue: Queue[AgentEvent] = Queue()

        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(queue)
        log = logging.getLogger(__name__)
        log.debug(
            "event_feed: subscribe | key=%s total_subscribers=%d",
            key,
            len(self._subscribers[key]),
        )

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers[key].remove(queue)
            if not self._subscribers[key]:
                del self._subscribers[key]
                log.debug("event_feed: unsubscribe | key=%s (no more subscribers)", key)
            else:
                log.debug(
                    "event_feed: unsubscribe | key=%s remaining_subscribers=%d",
                    key,
                    len(self._subscribers[key]),
                )

    async def request_confirmation(self, confirmation_id: str) -> PendingConfirmation:
        """Register a pending confirmation and return an awaitable handle.

        The caller broadcasts the confirmation_requested event separately
        with the full details (message, options, title, description), then
        awaits ``pending.resolved`` which is set when
        POST /agent/confirm/{confirmation_id} resolves it.
        """
        async with self._confirm_lock:
            pending = PendingConfirmation(confirmation_id=confirmation_id)
            self._pending_confirmations[confirmation_id] = pending
        return pending

    async def resolve_confirmation(
        self, confirmation_id: str, accepted: bool, response: str | None = None
    ) -> PendingConfirmation | None:
        """Resolve a pending confirmation by confirmation_id.

        Returns the resolved PendingConfirmation or None if not found / already resolved.
        """
        async with self._confirm_lock:
            pending = self._pending_confirmations.get(confirmation_id)
            if not pending or pending.resolved.is_set():
                return None

        pending.accepted = accepted
        pending.response = response
        pending.resolved.set()
        return pending

    def cleanup_session(self, session_id: str) -> None:
        """Remove sequence tracking for a completed session."""
        self._sequences.pop(session_id, None)
        self._locks.pop(session_id, None)

    async def broadcast_session(self, tenant_id: str, session: SessionResponse) -> None:
        """Notify tenant-level subscribers of a new or updated session."""
        for queue in self._session_subscribers.get(tenant_id, []):
            await queue.put(session)

    async def subscribe_sessions(
        self, tenant_id: str
    ) -> AsyncIterator[SessionResponse]:
        """Subscribe to session updates for a tenant."""
        queue: Queue[SessionResponse] = Queue()

        if tenant_id not in self._session_subscribers:
            self._session_subscribers[tenant_id] = []
        self._session_subscribers[tenant_id].append(queue)

        try:
            while True:
                session = await queue.get()
                yield session
        finally:
            self._session_subscribers[tenant_id].remove(queue)
            if not self._session_subscribers[tenant_id]:
                del self._session_subscribers[tenant_id]

    async def replay(
        self,
        tenant_id: str,
        session_id: str,
        after_sequence: int = 0,
    ) -> list[AgentEvent]:
        """Replay stored events from a sequence number."""
        tenant_oid = ObjectId(tenant_id)
        documents = (
            await AgentEventDocument.find(
                AgentEventDocument.tenant_id == tenant_oid,
                AgentEventDocument.session_id == session_id,
                AgentEventDocument.sequence > after_sequence,
            )
            .sort("sequence")
            .to_list(length=1000)
        )
        return [
            AgentEventBase.from_document(
                e.model_dump(by_alias=True, exclude={"tenant_id", "id"})
            )
            for e in documents
        ]
