"""Agent event feed for real-time streaming and persistence."""

from __future__ import annotations

from asyncio import Queue
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from canon_mcp.repositories.agent_events import AgentEventRepository


class AgentEventFeed:
    """Manages live event streaming and persistence for the Reasoning Feed.

    Assigns sequence numbers and timestamps centrally — callers provide
    type, author, content, and isFinal. This ensures globally ordered events
    regardless of whether they originate from the ReasoningFeedPlugin or the
    runner event loop.
    """

    def __init__(self, event_repo: AgentEventRepository) -> None:
        self._subscribers: dict[str, list[Queue[dict[str, Any]]]] = {}
        self._event_repo = event_repo
        self._sequences: dict[str, int] = {}  # run_id → current sequence

    async def broadcast(
        self,
        tenant_id: str,
        session_id: str,
        run_id: str,
        event: dict[str, Any],
    ) -> None:
        """Broadcast an event to subscribers and persist to agent_events.

        Assigns sequence number and timestamp if not already present.
        """
        # Assign sequence (monotonically increasing per run)
        seq = self._sequences.get(run_id, 0) + 1
        self._sequences[run_id] = seq
        event.setdefault("sequence", seq)
        event.setdefault("timestamp", datetime.now(UTC).isoformat())

        # Persist for replay
        await self._event_repo.insert(
            tenant_id=tenant_id,
            session_id=session_id,
            run_id=run_id,
            event=event,
        )

        # Fan out to live subscribers
        key = f"{tenant_id}:{session_id}"
        for queue in self._subscribers.get(key, []):
            await queue.put(event)

    async def subscribe(self, tenant_id: str, session_id: str) -> AsyncIterator[dict[str, Any]]:
        """Subscribe to live events for a session."""
        key = f"{tenant_id}:{session_id}"
        queue: Queue[dict[str, Any]] = Queue()

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

    async def replay(
        self,
        tenant_id: str,
        session_id: str,
        after_sequence: int = 0,
    ) -> list[dict[str, Any]]:
        """Replay stored events from a sequence number."""
        return await self._event_repo.list_after(
            tenant_id=tenant_id,
            session_id=session_id,
            after_sequence=after_sequence,
        )
