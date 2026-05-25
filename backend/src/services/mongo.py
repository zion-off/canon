"""MongoDB connection provider and index bootstrapper."""

from __future__ import annotations

import logging

from beanie import init_beanie
from pymongo import ASCENDING, DESCENDING, TEXT, AsyncMongoClient, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

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

logger = logging.getLogger(__name__)


class MongoProvider:
    """Provides database connection and initializes Beanie document models."""

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or settings.mongodb_uri
        self._client: AsyncMongoClient | None = None
        self._db: AsyncDatabase | None = None

    async def connect(self) -> None:
        """Initialize the MongoDB client and register Beanie document models."""
        from pymongo import AsyncMongoClient

        self._client = AsyncMongoClient(self._uri)
        self._db = self._client["canon"]
        await init_beanie(
            database=self._db,
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
        await self._create_indexes()

    async def _create_indexes(self) -> None:
        """Create compound and search indexes idempotently.

        Idempotent — ``create_indexes`` is a no-op if the index already exists.
        Search index creation is best-effort (logs warnings on failure).
        """
        db = self.db

        # ── Compound Indexes ────────────────────────────────────────────
        compound_indexes = {
            "users": [
                IndexModel([("email", ASCENDING)], unique=True),
                IndexModel([("tenantId", ASCENDING)]),
            ],
            "api_tokens": [
                IndexModel([("tokenHash", ASCENDING)], unique=True),
                IndexModel([("tenantId", ASCENDING)]),
            ],
            "invites": [
                IndexModel([("code", ASCENDING)], unique=True),
                IndexModel([("tenantId", ASCENDING), ("expiresAt", ASCENDING)]),
                IndexModel(
                    [("expiresAt", ASCENDING)],
                    expireAfterSeconds=0,
                ),
            ],
            "sessions": [
                IndexModel(
                    [
                        ("tenantId", ASCENDING),
                        ("userId", ASCENDING),
                        ("updatedAt", DESCENDING),
                    ]
                ),
                IndexModel([("sessionId", ASCENDING)], unique=True),
            ],
            "memory_nodes": [
                IndexModel([("tenantId", ASCENDING), ("name", ASCENDING)], unique=True),
                IndexModel([("tenantId", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("tenantId", ASCENDING), ("relatedEntityIds", ASCENDING)]),
                IndexModel([("tenantId", ASCENDING), ("supersedes", ASCENDING)]),
                IndexModel([("tenantId", ASCENDING), ("supersededBy", ASCENDING)]),
                IndexModel([("tenantId", ASCENDING), ("tags", ASCENDING)]),
                IndexModel(
                    [("name", TEXT), ("description", TEXT), ("content", TEXT)],
                    default_language="none",
                ),
            ],
            "agent_events": [
                IndexModel(
                    [
                        ("tenantId", ASCENDING),
                        ("sessionId", ASCENDING),
                        ("sequence", ASCENDING),
                    ]
                ),
                IndexModel(
                    [
                        ("tenantId", ASCENDING),
                        ("userId", ASCENDING),
                        ("createdAt", ASCENDING),
                    ]
                ),
            ],
        }

        for collection_name, indexes in compound_indexes.items():
            try:
                await db[collection_name].create_indexes(indexes)
            except Exception:
                logger.warning(
                    "Failed to create indexes for %s", collection_name, exc_info=True
                )

        # ── Search Indexes (Atlas Local / Atlas only) ───────────────────
        search_indexes = [
            {
                "name": "vector_search_index",
                "type": "vectorSearch",
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": 768,
                            "similarity": "cosine",
                        },
                        {
                            "type": "filter",
                            "path": "tenantId",
                        },
                        {
                            "type": "filter",
                            "path": "status",
                        },
                        {
                            "type": "filter",
                            "path": "tags",
                        },
                    ],
                },
            },
            {
                "name": "text_search_index",
                "type": "search",
                "definition": {
                    "mappings": {
                        "dynamic": False,
                        "fields": {
                            "name": [{"type": "string", "analyzer": "lucene.standard"}],
                            "description": [
                                {"type": "string", "analyzer": "lucene.standard"}
                            ],
                            "content": [
                                {"type": "string", "analyzer": "lucene.standard"}
                            ],
                            "tags": [{"type": "string", "analyzer": "lucene.keyword"}],
                            "status": [{"type": "string", "analyzer": "lucene.keyword"}],
                        },
                    },
                },
            },
        ]

        for index_def in search_indexes:
            try:
                await db.command(
                    "createSearchIndexes",
                    "memory_nodes",
                    indexes=[index_def],
                )
            except Exception:
                logger.warning(
                    "Failed to create search index '%s'. "
                    "Likely not running Atlas Local or Atlas.",
                    index_def["name"],
                    exc_info=True,
                )

    async def disconnect(self) -> None:
        """Close the MongoDB client connection."""
        if self._client:
            await self._client.close()

    @property
    def db(self) -> AsyncDatabase:
        """Return the canon database instance."""
        if self._db is None:
            raise RuntimeError("MongoProvider is not connected. Call connect() first.")
        return self._db
