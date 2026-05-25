"""Tenant resolution from API tokens."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from pydantic import Field

from src.models.documents import ApiTokenDocument
from src.models.schemas import MongoModel


class TenantContext(MongoModel):
    """Resolved tenant identity."""

    tenant_id: str = Field(validation_alias="tenantId")
    user_id: str = Field(validation_alias="userId")


class TenantResolver:
    """Resolves tenant identity from authentication tokens."""

    async def resolve(self, raw_token: str) -> TenantContext | None:
        """Resolve a raw token string to a TenantContext.

        Hashes the token with SHA-256, looks up in api_tokens collection,
        and updates lastUsedAt on successful resolution.
        """
        token_hash = sha256(raw_token.encode()).hexdigest()
        api_token = await ApiTokenDocument.find_one(
            ApiTokenDocument.token_hash == token_hash
        )

        if not api_token:
            return None

        await ApiTokenDocument.find_one({"_id": api_token.id}).set(
            {ApiTokenDocument.last_used_at: datetime.now(UTC)}
        )

        data = api_token.model_dump(by_alias=True)
        # Fallback for old records without userId
        data.setdefault("userId", data.get("tenantId"))
        return TenantContext.model_validate(data)
