"""Beanie ODM document models — one per MongoDB collection.

All fields use snake_case Python names with camelCase aliases matching
the existing MongoDB schema. No data migration needed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie import Document
from beanie.odm.fields import PydanticObjectId
from pydantic import Field


class UserDocument(Document):
    email: str
    name: str
    password_hash: str = Field(alias="passwordHash")
    tenant_id: PydanticObjectId | None = Field(default=None, alias="tenantId")
    role: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Settings:
        name = "users"
        use_aliases = True


class TenantDocument(Document):
    name: str
    slug: str
    embedding_model: str = Field(alias="embeddingModel")
    created_at: datetime = Field(alias="createdAt")
    settings: dict[str, Any] = Field(default_factory=lambda: {"maxGraphDepth": 2})

    class Settings:
        name = "tenants"
        use_aliases = True


class ApiTokenDocument(Document):
    tenant_id: PydanticObjectId = Field(alias="tenantId")
    user_id: str = Field(alias="userId")
    token_hash: str = Field(alias="tokenHash")
    label: str
    created_at: datetime = Field(alias="createdAt")
    last_used_at: datetime | None = Field(default=None, alias="lastUsedAt")

    class Settings:
        name = "api_tokens"
        use_aliases = True


class InviteDocument(Document):
    tenant_id: PydanticObjectId = Field(alias="tenantId")
    code: str
    created_by: PydanticObjectId = Field(alias="createdBy")
    uses_remaining: int = Field(alias="usesRemaining")
    expires_at: datetime = Field(alias="expiresAt")
    created_at: datetime = Field(alias="createdAt")

    class Settings:
        name = "invites"
        use_aliases = True


class SessionDocument(Document):
    session_id: str = Field(alias="sessionId")
    tenant_id: PydanticObjectId = Field(alias="tenantId")
    user_id: str = Field(alias="userId")
    title: str
    summary: str | None = None
    run_count: int = Field(default=0, alias="runCount")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    last_run_at: datetime | None = Field(default=None, alias="lastRunAt")

    class Settings:
        name = "sessions"
        use_aliases = True


class MemoryNodeDocument(Document):
    tenant_id: PydanticObjectId = Field(alias="tenantId")
    name: str
    description: str | None = None
    content: str | None = None
    status: str
    related_entity_ids: list[PydanticObjectId] = Field(
        default_factory=list, alias="relatedEntityIds"
    )
    supersedes: PydanticObjectId | None = None
    superseded_by: PydanticObjectId | None = Field(default=None, alias="supersededBy")
    tags: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
    embedding_text: str | None = Field(default=None, alias="embeddingText")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "memory_nodes"
        use_aliases = True


class AgentEventDocument(Document):
    tenant_id: PydanticObjectId = Field(alias="tenantId")
    user_id: str = Field(alias="userId")
    session_id: str = Field(alias="sessionId")
    run_id: str = Field(alias="runId")
    type: str
    author: str | None = None
    content: str | None = None
    sequence: int
    timestamp: str | None = None
    is_final: bool = Field(default=False, alias="isFinal")
    created_at: datetime = Field(alias="createdAt")

    class Settings:
        name = "agent_events"
        use_aliases = True
