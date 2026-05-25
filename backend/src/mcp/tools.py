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
from src.mcp.constants import SessionState, TempState
from src.mcp.models import (
    EmbeddingError,
    EmbeddingResult,
    EmbeddingSuccess,
    EmitCheckpointResult,
    MemoryNodeInput,
    PrepareError,
    PrepareResult,
    PrepareSuccess,
    RelationshipMeta,
)
from src.mcp.utils import get_genai_client

# ─── Embedding Utilities ─────────────────────────────────────────────────────


def build_embedding_text(doc: MemoryNodeInput) -> str:
    """Build a retrieval-optimized semantic representation of a memory node.

    Combines the node's name, status, description, content, and tags into
    a single string optimized for embedding-based similarity search.
    Content is capped at 1500 characters to stay within model limits.
    """
    lines: list[str] = []
    header = doc.name
    if doc.status:
        header += f" [{doc.status}]"
    lines.append(header)
    if doc.description:
        lines.append(doc.description)
    if doc.content:
        lines.append(doc.content[:1500])
    if doc.tags:
        lines.append("Tags: " + ", ".join(doc.tags))
    return "\n".join(filter(None, lines))


async def generate_document_embedding(text: str) -> list[float]:
    """Generate a 768-dimensional embedding for document storage.

    Uses the Gemini embedding API with RETRIEVAL_DOCUMENT task type,
    optimized for indexing documents that will later be retrieved via
    query embeddings.
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


async def embed_query(text: str) -> EmbeddingResult:
    """Generate a 768-dimensional embedding for query-time vector search.

    Uses the Gemini embedding API with RETRIEVAL_QUERY task type,
    optimized for finding documents that match the query semantically.

    Args:
        text: The query text to embed.

    Returns:
        An EmbeddingSuccess containing the 768-float vector, or
        an EmbeddingError on failure.
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
            return EmbeddingError(error="Embedding API returned empty response.")
        values = response.embeddings[0].values
        if values is None:
            return EmbeddingError(error="Embedding API returned None values.")
        return EmbeddingSuccess(embedding=values)
    except Exception as exc:
        return EmbeddingError(error=f"Embedding generation failed: {exc}")


# ─── Core Agent Tools ────────────────────────────────────────────────────────


async def prepare_embedding(
    document: dict[str, Any],
    rationale: str,
    related_existing_ids: list[str],
    tool_context: ToolContext,
) -> PrepareResult:
    """Validate and precompute an embedding for a memory node.

    Validates the document, generates a retrieval-optimized embedding, and
    returns a fully prepared document ready for insertion via the MongoDB MCP
    server's ``insert-many`` tool. Persistence is handled by the memory_writer
    subagent using MCP ``insert-many`` and ``update-many`` tools.

    Args:
        document: The memory node data matching the MemoryNodeInput schema.
        rationale: Explanation of why this node is being created or updated.
        related_existing_ids: List of existing node IDs (as hex strings) that
            this node should be linked to bidirectionally.
        tool_context: ADK tool context providing access to agent state.

    Returns:
        A PrepareSuccess with the prepared document and relationship metadata,
        or a PrepareError on validation or generation failure.
    """
    tenant_id = ObjectId(tool_context.state[SessionState.TENANT_ID])

    try:
        doc = MemoryNodeInput.model_validate(document)
    except Exception as exc:
        return PrepareError(error=f"Invalid document: {exc}")

    if len(doc.related_entity_ids) > 100:
        return PrepareError(error="relatedEntityIds exceeds maximum of 100 entries.")

    try:
        related_object_ids = [ObjectId(rid) for rid in related_existing_ids]
        related_entity_object_ids = [ObjectId(rid) for rid in doc.related_entity_ids]
    except Exception:
        return PrepareError(error="Invalid ObjectId in related IDs.")

    supersedes_id: ObjectId | None = None
    if doc.supersedes:
        try:
            supersedes_id = ObjectId(doc.supersedes)
        except Exception:
            return PrepareError(error="Invalid ObjectId in supersedes.")

    # Build the insertion-ready document.
    now = datetime.now(tz=UTC)
    embedding_text = build_embedding_text(doc)

    try:
        embedding = await generate_document_embedding(embedding_text)
    except Exception as exc:
        return PrepareError(error=f"Embedding generation failed: {exc}")

    prepared: dict[str, Any] = {
        "name": doc.name,
        "description": doc.description,
        "content": doc.content,
        "status": doc.status,
        "tags": doc.tags,
        "metadata": doc.metadata,
        "tenantId": str(tenant_id),
        "relatedEntityIds": [str(o) for o in related_entity_object_ids],
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat(),
        "supersedes": str(supersedes_id) if supersedes_id else None,
        "embeddingText": embedding_text,
        "embedding": embedding,
    }

    meta = RelationshipMeta(
        supersedes_id_str=str(supersedes_id) if supersedes_id else None,
        related_existing_id_strs=[str(o) for o in related_object_ids],
    )

    return PrepareSuccess(status="ready", document=prepared, meta=meta)


async def emit_checkpoint(
    message: str, tool_context: ToolContext
) -> EmitCheckpointResult:
    """Emit a reasoning checkpoint visible to the user.

    Checkpoints allow agents to communicate intermediate reasoning steps
    and progress updates during long-running operations.

    Args:
        message: The checkpoint message describing current reasoning state.
        tool_context: ADK tool context for accessing agent state.

    Returns:
        A confirmation that the checkpoint was emitted.
    """
    checkpoints: list[dict[str, Any]] = tool_context.state.get(
        TempState.CHECKPOINTS, []
    )
    checkpoints.append({"message": message, "timestamp": datetime.now(UTC).isoformat()})
    tool_context.state[TempState.CHECKPOINTS] = checkpoints
    return EmitCheckpointResult(status="emitted", message=message)


# ─── Tool Instances ──────────────────────────────────────────────────────────

prepare_embedding_tool = FunctionTool(func=prepare_embedding)
embed_query_tool = FunctionTool(func=embed_query)
emit_checkpoint_tool = FunctionTool(func=emit_checkpoint)
