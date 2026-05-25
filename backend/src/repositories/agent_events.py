"""Repository for agent event persistence."""

from __future__ import annotations

from typing import Any

from bson import ObjectId

from src.models.documents import AgentEventDocument


class AgentEventRepository:
    """Handles persistence of agent reasoning events."""

    async def insert(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        run_id: str,
        event: dict[str, Any],
    ) -> None:
        """Insert a single agent event into the agent_events collection."""
        doc = AgentEventDocument.model_construct(
            tenant_id=ObjectId(tenant_id),
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            **event,
        )
        await doc.insert()

    async def list_after(
        self,
        tenant_id: str,
        session_id: str,
        after_sequence: int = 0,
    ) -> list[dict[str, Any]]:
        """List events after a given sequence number for replay."""
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
            e.model_dump(by_alias=True, exclude={"tenant_id", "_id"}) for e in events
        ]
