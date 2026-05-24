"""Repository for agent event persistence."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class AgentEventRepository:
    """Handles persistence of agent reasoning events."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def insert(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        run_id: str,
        event: dict[str, Any],
    ) -> None:
        """Insert a single agent event into the agent_events collection."""
        doc = {
            "tenantId": ObjectId(tenant_id),
            "userId": user_id,
            "sessionId": session_id,
            "runId": run_id,
            **event,
        }
        await self._db.agent_events.insert_one(doc)

    async def list_after(
        self,
        tenant_id: str,
        session_id: str,
        after_sequence: int = 0,
    ) -> list[dict[str, Any]]:
        """List events after a given sequence number for replay."""
        cursor = self._db.agent_events.find(
            {
                "tenantId": ObjectId(tenant_id),
                "sessionId": session_id,
                "sequence": {"$gt": after_sequence},
            },
            {"_id": 0, "tenantId": 0},
        ).sort("sequence", 1)
        return await cursor.to_list(length=1000)
