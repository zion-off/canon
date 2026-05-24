"""ADK agent tools for the Canon memory graph.

Provides tools that agents use to persist structured memory nodes,
generate embeddings, and emit reasoning checkpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from bson import ObjectId
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from src.config import get_settings

# ─── Model Configuration ─────────────────────────────────────────────────────

REASONING_MODEL: str = get_settings().reasoning_model
FAST_MODEL: str = get_settings().fast_model
EMBEDDING_MODEL: str = get_settings().embedding_model

# ─── Lazy MongoDB Client ─────────────────────────────────────────────────────

_mongo_client: AsyncIOMotorClient | None = None


def _get_mongo_client() -> AsyncIOMotorClient:
    """Return a lazily-initialized MongoDB client singleton."""
    global _mongo_client  # noqa: PLW0603
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(get_settings().mongodb_uri)
    return _mongo_client


# ─── Embedding Utilities ─────────────────────────────────────────────────────


def build_embedding_text(document: dict) -> str:
    """Build a retrieval-optimized semantic representation of a memory node.

    Combines the node's name, status, description, content, and tags into
    a single string optimized for embedding-based similarity search.
    Content is capped at 1500 characters.

    Args:
        document: A memory node dictionary.

    Returns:
        A formatted string suitable for embedding generation.
    """
    name = document.get("name", "")
    description = document.get("description", "")
    content = document.get("content", "")
    status = document.get("status", "")
    tags = document.get("tags", [])

    lines: list[str] = []
    header = name
    if status:
        header += f" [{status}]"
    lines.append(header)
    if description:
        lines.append(description)
    if content:
        lines.append(content[:1500])
    if tags:
        lines.append(f"Tags: {', '.join(tags)}")
    return "\n".join(filter(None, lines))


async def generate_document_embedding(text: str) -> list[float]:
    """Generate a 768-dimensional embedding for document storage.

    Uses the Gemini embedding API with RETRIEVAL_DOCUMENT task type,
    optimized for indexing documents that will later be retrieved via
    query embeddings.

    Args:
        text: The text content to embed.

    Returns:
        A list of 768 floats representing the embedding vector.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent",
            params={"key": get_settings().gemini_api_key},
            json={
                "model": f"models/{EMBEDDING_MODEL}",
                "content": {"parts": [{"text": text}]},
                "taskType": "RETRIEVAL_DOCUMENT",
                "outputDimensionality": 768,
            },
        )
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
    """
    model = EMBEDDING_MODEL
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
            params={"key": get_settings().gemini_api_key},
            json={
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]},
                "taskType": "RETRIEVAL_QUERY",
                "outputDimensionality": 768,
            },
        )
        data = response.json()
    return {"embedding": data["embedding"]["values"]}


# ─── Core Agent Tools ────────────────────────────────────────────────────────


async def canonize_node(
    document: dict,
    rationale: str,
    related_existing_ids: list[str],
    tool_context: ToolContext,
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
        A dictionary with 'status', 'node_id', and 'name' on success,
        or 'error' on validation/persistence failure.
    """
    tenant_id = ObjectId(tool_context.state["app:tenant_id"])
    document["tenantId"] = tenant_id

    # Validate required fields
    required_fields = ("name", "description", "content", "status", "tenantId")
    missing = [f for f in required_fields if not document.get(f)]
    if missing:
        return {"error": f"Missing required fields: {', '.join(missing)}"}

    # Validate relatedEntityIds cardinality
    related_entity_ids = document.get("relatedEntityIds", [])
    if len(related_entity_ids) > 100:
        return {"error": "relatedEntityIds exceeds maximum of 100 entries."}

    # Convert string IDs to ObjectIds
    try:
        related_object_ids = [ObjectId(rid) for rid in related_existing_ids]
        related_entity_object_ids = [ObjectId(rid) for rid in related_entity_ids]
    except Exception:
        return {"error": "Invalid ObjectId in related IDs."}

    document["relatedEntityIds"] = related_entity_object_ids

    # Handle supersedes field
    supersedes_id: ObjectId | None = None
    if document.get("supersedes"):
        try:
            supersedes_id = ObjectId(document["supersedes"])
            document["supersedes"] = supersedes_id
        except Exception:
            return {"error": "Invalid ObjectId in supersedes."}

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
        return {"error": f"Embedding generation failed: {exc}"}

    document["embedding"] = embedding

    # Insert into MongoDB
    client = _get_mongo_client()
    db = client["canon"]
    collection = db["memory_nodes"]

    try:
        result = await collection.insert_one(document)
    except DuplicateKeyError as exc:
        return {"error": f"Duplicate key: {exc}"}

    node_id = result.inserted_id

    # Update bidirectional edges on related nodes (scoped by tenantId)
    if related_object_ids:
        await collection.update_many(
            {"_id": {"$in": related_object_ids}, "tenantId": tenant_id},
            {
                "$addToSet": {"relatedEntityIds": node_id},
                "$set": {"updatedAt": now},
            },
        )

    # Mark superseded node as deprecated
    if supersedes_id:
        await collection.update_one(
            {"_id": supersedes_id, "tenantId": tenant_id},
            {
                "$set": {
                    "status": "deprecated",
                    "supersededBy": node_id,
                    "updatedAt": now,
                },
            },
        )

    # Store result in tool context state
    tool_context.state["temp:last_write"] = {
        "node_id": str(node_id),
        "name": document["name"],
    }

    return {
        "status": "written",
        "node_id": str(node_id),
        "name": document["name"],
    }


async def emit_checkpoint(message: str, tool_context: ToolContext) -> dict:
    """Emit a reasoning checkpoint visible to the user.

    Checkpoints allow agents to communicate intermediate reasoning steps
    and progress updates during long-running operations.

    Args:
        message: The checkpoint message describing current reasoning state.
        tool_context: ADK tool context for accessing agent state.

    Returns:
        A dictionary confirming the checkpoint was emitted.
    """
    checkpoints = tool_context.state.get("temp:checkpoints", [])
    checkpoints.append(
        {"message": message, "timestamp": datetime.now(UTC).isoformat()}
    )
    tool_context.state["temp:checkpoints"] = checkpoints
    return {"status": "emitted", "message": message}


# ─── Tool Instances ──────────────────────────────────────────────────────────

canonize_node_tool = FunctionTool(func=canonize_node)
embed_query_tool = FunctionTool(func=generate_query_embedding, name="embed_query")
emit_checkpoint_tool = FunctionTool(func=emit_checkpoint)
