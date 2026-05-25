"""Agent event feed for real-time streaming and persistence."""

from __future__ import annotations

from asyncio import Queue
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from bson import ObjectId

from src.models.documents import AgentEventDocument
from src.models.schemas import AgentEvent


class AgentEventFeed:
    """Manages live event streaming and persistence for the Reasoning Feed.

    Assigns sequence numbers and timestamps centrally — callers provide
    type, author, content, and isFinal. This ensures globally ordered events
    regardless of whether they originate from the ReasoningFeedPlugin or the
    runner event loop.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Queue[AgentEvent]]] = {}
        self._sequences: dict[str, int] = {}  # run_id → current sequence

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
        # Assign sequence (monotonically increasing per run)
        seq = self._sequences.get(run_id, 0) + 1
        self._sequences[run_id] = seq
        if event.sequence is None:
            event.sequence = seq
        if event.timestamp is None:
            event.timestamp = datetime.now(UTC).isoformat()

        # Serialize to dict for persistence
        event_dict = event.model_dump(by_alias=True)

        # Persist for replay
        doc = AgentEventDocument.model_construct(
            tenant_id=ObjectId(tenant_id),
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            **event_dict,
        )
        await doc.insert()

        # Fan out AgentEvent objects to live subscribers
        key = f"{tenant_id}:{session_id}"
        for queue in self._subscribers.get(key, []):
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

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers[key].remove(queue)
            if not self._subscribers[key]:
                del self._subscribers[key]

    def cleanup_run(self, run_id: str) -> None:
        """Remove sequence tracking for a completed run."""
        self._sequences.pop(run_id, None)

    async def replay(
        self,
        tenant_id: str,
        session_id: str,
        after_sequence: int = 0,
    ) -> list[AgentEvent]:
        """Replay stored events from a sequence number."""
        tenant_oid = ObjectId(tenant_id)
        events = (
            await AgentEventDocument.find(
                {
                    "tenant_id": tenant_oid,
                    "session_id": session_id,
                    "sequence": {"$gt": after_sequence},
                }
            )
            .sort("sequence")
            .to_list(length=1000)
        )
        return [
            AgentEvent.model_validate(
                e.model_dump(by_alias=True, exclude={"tenant_id", "_id"})
            )
            for e in events
        ]
