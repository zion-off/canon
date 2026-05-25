"""MongoDB connection provider and Beanie initializer."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.config import settings
from src.models.documents import (
    AgentEventDocument,
    ApiTokenDocument,
    InviteDocument,
    MemoryNodeDocument,
    SessionDocument,
    TenantDocument,
    UserDocument,
)

if TYPE_CHECKING:
    from pymongo.asynchronous.database import AsyncDatabase


class MongoProvider:
    """Provides database connection and initializes Beanie document models."""

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or settings.mongodb_uri
        self._client: AsyncIOMotorClient | None = None

    async def connect(self) -> None:
        """Initialize the MongoDB client and register Beanie document models."""
        self._client = AsyncIOMotorClient(self._uri)
        await init_beanie(
            database=cast("AsyncDatabase", self.db),
            document_models=[
                UserDocument,
                TenantDocument,
                ApiTokenDocument,
                InviteDocument,
                SessionDocument,
                MemoryNodeDocument,
                AgentEventDocument,
            ],
        )

    async def disconnect(self) -> None:
        """Close the MongoDB client connection."""
        if self._client:
            self._client.close()

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Return the canon database instance."""
        if self._client is None:
            raise RuntimeError("MongoProvider is not connected. Call connect() first.")
        return self._client["canon"]
