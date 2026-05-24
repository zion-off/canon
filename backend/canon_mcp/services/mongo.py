"""MongoDB connection provider."""

from __future__ import annotations

import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class MongoProvider:
    """Provides database connection."""

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or os.environ["MONGODB_URI"]
        self._client: AsyncIOMotorClient | None = None

    async def connect(self) -> None:
        self._client = AsyncIOMotorClient(self._uri)

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._client is None:
            raise RuntimeError("MongoProvider is not connected. Call connect() first.")
        return self._client["canon"]
