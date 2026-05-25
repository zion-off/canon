"""ADK agent tools for the Canon memory graph.

Provides tools that agents use to generate embeddings for memory nodes,
prepare documents for persistence, and emit reasoning checkpoints.

All database operations go through the MongoDB MCP server —
this module only handles validation, embedding generation, and document
preparation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from src.config import settings
from src.mcp.utils import get_genai_client

# ─── Embedding Utilities ─────────────────────────────────────────────────────


def build_embedding_text(document: dict[str, Any]) -> str:
    """Build a retrieval-optimized semantic representation of a memory node.

    Combines the node's name, status, description, content, and tags into
    a single string optimized for embedding-based similarity search.
    Content is capped at 1500 characters to stay within model limits.

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
        lines.append("Tags: " + ", ".join(tags))
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
    client = get_genai_client()
    response = await client.aio.models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )
    if not response.embeddings:
        raise RuntimeError("Embedding API returned empty response.")
    values = response.embeddings[0].values
    if values is None:
        raise RuntimeError("Embedding API returned None values.")
    return values


async def embed_query(text: str) -> dict[str, list[float]]:
    """Generate a 768-dimensional embedding for query-time vector search.

    Uses the Gemini embedding API with RETRIEVAL_QUERY task type,
    optimized for finding documents that match the query semantically.

    Args:
        text: The query text to embed.

    Returns:
        A dictionary with key 'embedding' containing the 768-float vector,
        or an 'error' key on failure.
    """
    client = get_genai_client()
    try:
        response = await client.aio.models.embed_content(
            model=settings.embedding_model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )
        if not response.embeddings:
            return {"error": "Embedding API returned empty response."}  # type: ignore[dict-item]
        values = response.embeddings[0].values
        if values is None:
            return {"error": "Embedding API returned None values."}  # type: ignore[dict-item]
        return {"embedding": values}
    except Exception as exc:
        return {"error": f"Embedding generation failed: {exc}"}  # type: ignore[dict-item]


# ─── Core Agent Tools ────────────────────────────────────────────────────────


async def prepare_embedding(
    document: dict[str, Any],
    rationale: str,
    related_existing_ids: list[str],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Validate and precompute an embedding for a memory node.

    Validates the document, generates a retrieval-optimized embedding, and
    returns a fully prepared document ready for insertion via the MongoDB MCP
    server's ``insert-many`` tool. Persistence is handled by the memory_writer
    subagent using MCP ``insert-many`` and ``update-many`` tools.

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
        A dictionary with 'document' (the prepared document ready for
        insertion) and metadata about relationships to form, or 'error'
        on validation/failure.
    """
    tenant_id = ObjectId(tool_context.state["app:tenant_id"])
    document["tenantId"] = tenant_id

    # Validate required fields
    required_fields = ("name", "description", "content", "status", "tenantId")
    missing = [f for f in required_fields if not document.get(f)]
    if missing:
        sep = ", "
        return {"error": f"Missing required fields: {sep.join(missing)}"}

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

    # Serialize ObjectId fields to hex strings and dates to ISO strings
    # so the returned dict is JSON-serializable for ADK framework.
    document["tenantId"] = str(tenant_id)
    document["relatedEntityIds"] = [str(o) for o in related_entity_object_ids]
    document["createdAt"] = now.isoformat()
    document["updatedAt"] = now.isoformat()
    if supersedes_id:
        document["supersedes"] = str(supersedes_id)
    if "supersededBy" in document:
        del document["supersededBy"]

    meta = {
        "supersedes_id_str": str(supersedes_id) if supersedes_id else None,
        "related_existing_id_strs": [str(o) for o in related_object_ids],
    }

    return {
        "status": "ready",
        "document": document,
        "meta": meta,
    }


async def emit_checkpoint(message: str, tool_context: ToolContext) -> dict[str, str]:
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
    checkpoints.append({"message": message, "timestamp": datetime.now(UTC).isoformat()})
    tool_context.state["temp:checkpoints"] = checkpoints
    return {"status": "emitted", "message": message}


# ─── Tool Instances ──────────────────────────────────────────────────────────

prepare_embedding_tool = FunctionTool(func=prepare_embedding)
embed_query_tool = FunctionTool(func=embed_query)
emit_checkpoint_tool = FunctionTool(func=emit_checkpoint)
