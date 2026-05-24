"""ADK agent tools for the Canon memory graph.

Provides tools that agents use to persist structured memory nodes,
generate embeddings, and emit reasoning checkpoints.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx
from bson import ObjectId
from google.adk.tools import FunctionTool
from motor.motor_asyncio import AsyncIOMotorClient

# ─── Model Configuration ─────────────────────────────────────────────────────

REASONING_MODEL: str = os.environ.get("CANON_REASONING_MODEL", "gemini-2.5-pro")
FAST_MODEL: str = os.environ.get("CANON_FAST_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL: str = os.environ.get("CANON_EMBEDDING_MODEL", "text-embedding-004")

# ─── Lazy MongoDB Client ─────────────────────────────────────────────────────

_mongo_client: AsyncIOMotorClient | None = None


def _get_mongo_client() -> AsyncIOMotorClient:
    """Return a lazily-initialized MongoDB client singleton.

    Reads MONGODB_URI from environment on first call. Subsequent calls
    return the cached client instance.
    """
    global _mongo_client  # noqa: PLW0603
    if _mongo_client is None:
        uri = os.environ["MONGODB_URI"]
        _mongo_client = AsyncIOMotorClient(uri)
    return _mongo_client


# ─── Embedding Utilities ─────────────────────────────────────────────────────


def build_embedding_text(document: dict) -> str:
    """Build a retrieval-optimized semantic representation of a memory node.

    Combines the node's name, description, content, tags, and status into
    a single string optimized for embedding-based similarity search.

    Args:
        document: A memory node dictionary containing at minimum 'name',
            'description', and 'content' fields.

    Returns:
        A formatted string suitable for embedding generation.
    """
    parts: list[str] = []

    name = document.get("name", "")
    if name:
        parts.append(f"Name: {name}")

    description = document.get("description", "")
    if description:
        parts.append(f"Description: {description}")

    content = document.get("content", "")
    if content:
        parts.append(f"Content: {content}")

    tags = document.get("tags", [])
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")

    status = document.get("status", "")
    if status:
        parts.append(f"Status: {status}")

    return "\n".join(parts)


async def generate_document_embedding(text: str) -> list[float]:
    """Generate a 768-dimensional embedding for document storage.

    Uses the Gemini embedding API with RETRIEVAL_DOCUMENT task type,
    optimized for indexing documents that will later be retrieved via
    query embeddings.

    Args:
        text: The text content to embed.

    Returns:
        A list of 768 floats representing the embedding vector.

    Raises:
        httpx.HTTPStatusError: If the Gemini API returns a non-2xx response.
        KeyError: If GEMINI_API_KEY is not set in environment.
    """
    api_key = os.environ["GEMINI_API_KEY"]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{EMBEDDING_MODEL}:embedContent?key={api_key}"
    )
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_DOCUMENT",
        "outputDimensionality": 768,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()

    data = response.json()
    return data["embedding"]["values"]


async def generate_query_embedding(text: str) -> dict:
    """Generate a 768-dimensional embedding for query-time vector search.

    Uses the Gemini embedding API with RETRIEVAL_QUERY task type,
    optimized for finding documents that match the query semantically.

    Args:
        text: The query text to embed.

    Returns:
        A dictionary with key 'embedding' containing the 768-float vector.

    Raises:
        httpx.HTTPStatusError: If the Gemini API returns a non-2xx response.
        KeyError: If GEMINI_API_KEY is not set in environment.
    """
    api_key = os.environ["GEMINI_API_KEY"]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{EMBEDDING_MODEL}:embedContent?key={api_key}"
    )
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY",
        "outputDimensionality": 768,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()

    data = response.json()
    return {"embedding": data["embedding"]["values"]}


# ─── Core Agent Tools ────────────────────────────────────────────────────────


async def canonize_node(
    document: dict,
    rationale: str,
    related_existing_ids: list[str],
    tool_context: Any,
) -> dict:
    """Persist a structured memory node to the Canon knowledge graph.

    Creates a new node in the memory_nodes collection with full validation,
    embedding generation, bidirectional edge management, and supersession
    handling.

    Args:
        document: The memory node data. Must include 'name', 'description',
            'content', and 'status' fields. May include 'tags', 'supersedes',
            and 'relatedEntityIds'.
        rationale: Explanation of why this node is being created or updated.
        related_existing_ids: List of existing node IDs (as hex strings) that
            this node should be linked to bidirectionally.
        tool_context: ADK tool context providing access to agent state.
            Must have state["app:tenant_id"] set.

    Returns:
        A dictionary with 'status', 'nodeId', and 'message' on success,
        or 'status' and 'error' on validation failure.
    """
    # Force tenant isolation
    tenant_id = tool_context.state.get("app:tenant_id")
    if not tenant_id:
        return {"status": "error", "error": "Missing tenant_id in agent state."}
    document["tenantId"] = tenant_id

    # Validate required fields
    required_fields = ("name", "description", "content", "status", "tenantId")
    missing = [f for f in required_fields if not document.get(f)]
    if missing:
        return {
            "status": "error",
            "error": f"Missing required fields: {', '.join(missing)}",
        }

    # Validate relatedEntityIds cardinality
    related_entity_ids = document.get("relatedEntityIds", [])
    if len(related_entity_ids) > 100:
        return {
            "status": "error",
            "error": "relatedEntityIds exceeds maximum of 100 entries.",
        }

    # Convert string IDs to ObjectIds
    try:
        related_object_ids = [ObjectId(rid) for rid in related_existing_ids]
        related_entity_object_ids = [ObjectId(rid) for rid in related_entity_ids]
    except Exception:
        return {"status": "error", "error": "Invalid ObjectId in related IDs."}

    document["relatedEntityIds"] = related_entity_object_ids

    # Handle supersedes field
    supersedes_id: ObjectId | None = None
    if document.get("supersedes"):
        try:
            supersedes_id = ObjectId(document["supersedes"])
            document["supersedes"] = supersedes_id
        except Exception:
            return {"status": "error", "error": "Invalid ObjectId in supersedes."}

    # Set timestamps
    now = datetime.now(tz=UTC)
    document["createdAt"] = now
    document["updatedAt"] = now

    # Build embedding text and generate embedding
    embedding_text = build_embedding_text(document)
    document["embeddingText"] = embedding_text

    try:
        embedding = await generate_document_embedding(embedding_text)
    except Exception as exc:
        return {"status": "error", "error": f"Embedding generation failed: {exc}"}

    document["embedding"] = embedding

    # Store rationale as metadata
    document["_rationale"] = rationale

    # Insert into MongoDB
    client = _get_mongo_client()
    db = client["canon"]
    collection = db["memory_nodes"]

    result = await collection.insert_one(document)
    node_id = result.inserted_id

    # Update bidirectional edges on related nodes
    if related_object_ids:
        await collection.update_many(
            {"_id": {"$in": related_object_ids}},
            {
                "$addToSet": {"relatedEntityIds": node_id},
                "$set": {"updatedAt": now},
            },
        )

    # Mark superseded node as deprecated
    if supersedes_id:
        await collection.update_one(
            {"_id": supersedes_id},
            {
                "$set": {
                    "status": "deprecated",
                    "supersededBy": node_id,
                    "updatedAt": now,
                },
            },
        )

    # Store result in tool context state
    write_result = {
        "status": "success",
        "nodeId": str(node_id),
        "message": f"Node '{document['name']}' persisted successfully.",
    }
    tool_context.state["temp:last_write"] = write_result

    return write_result


async def emit_checkpoint(message: str, tool_context: Any) -> dict:
    """Emit a reasoning checkpoint visible to the user.

    Checkpoints allow agents to communicate intermediate reasoning steps
    and progress updates during long-running operations.

    Args:
        message: The checkpoint message describing current reasoning state.
        tool_context: ADK tool context for accessing agent state.

    Returns:
        A dictionary confirming the checkpoint was emitted.
    """
    checkpoint = {
        "type": "reasoning_checkpoint",
        "content": message,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    tool_context.state["temp:last_checkpoint"] = checkpoint
    return {"status": "emitted", "checkpoint": checkpoint}


# ─── Tool Instances ──────────────────────────────────────────────────────────

embed_query_tool = FunctionTool(func=generate_query_embedding, name="embed_query")
canonize_node_tool = FunctionTool(func=canonize_node)
emit_checkpoint_tool = FunctionTool(func=emit_checkpoint)
