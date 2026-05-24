"""MongoDB connection provider."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.config import settings


class MongoProvider:
    """Provides database connection."""

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or settings.mongodb_uri
        self._client: AsyncIOMotorClient | None = None

    async def connect(self) -> None:
        """Initialize the MongoDB client connection."""
        self._client = AsyncIOMotorClient(self._uri)

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
