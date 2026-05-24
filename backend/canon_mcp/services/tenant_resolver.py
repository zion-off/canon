"""Tenant resolution from API tokens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from motor.motor_asyncio import AsyncIOMotorDatabase


@dataclass
class TenantContext:
    """Resolved tenant identity."""
    tenant_id: str
    user_id: str


class TenantResolver:
    """Resolves tenant identity from authentication tokens."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def resolve(self, raw_token: str) -> TenantContext | None:
        """Resolve a raw token string to a TenantContext.

        Hashes the token with SHA-256, looks up in api_tokens collection,
        and updates lastUsedAt on successful resolution.
        """
        token_hash = sha256(raw_token.encode()).hexdigest()
        record = await self._db.api_tokens.find_one({"token": token_hash})

        if not record:
            return None

        await self._db.api_tokens.update_one(
            {"_id": record["_id"]},
            {"$set": {"lastUsedAt": datetime.now(UTC)}},
        )

        return TenantContext(
            tenant_id=str(record["tenantId"]),
            user_id=str(record.get("userId", record["tenantId"])),
        )
