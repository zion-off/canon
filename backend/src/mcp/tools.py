"""ADK agent tools for the Canon memory graph.

Provides tools that agents use for hybrid search, embedding generation,
document preparation, and reasoning checkpoints.

Semantic retrieval (hybrid_search) generates embeddings and calls the
MongoDB MCP server's aggregate tool internally — the LLM never sees
raw vectors. All other database operations go through the MongoDB MCP
server directly via agent tool bindings.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import TextContent

from mcp import ClientSession
from src.config import settings
from src.mcp.constants import Database, SessionState, TempState
from src.mcp.models import (
    EmitCheckpointResult,
    HybridSearchError,
    HybridSearchResult,
    HybridSearchSuccess,
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


async def _generate_query_embedding(text: str) -> list[float]:
    """Generate a 768-dim query embedding via Gemini."""
    client = get_genai_client()
    response = await client.aio.models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )
    if not response.embeddings:
        raise RuntimeError("Embedding API returned empty response.")
    values = response.embeddings[0].values
    if values is None:
        raise RuntimeError("Embedding API returned None values.")
    return values


async def hybrid_search(
    query: str,
    keywords: list[str] | None = None,
    limit: int = 10,
    tool_context: ToolContext | None = None,
) -> HybridSearchResult:
    """Search memory nodes via hybrid semantic and keyword search.

    Generates a query embedding and executes a ``$rankFusion`` pipeline
    against the MongoDB MCP server — the LLM never handles raw vectors.

    The pipeline combines:
    - ``$vectorSearch`` (semantic) weighted 1.5x
    - ``$search`` on ``name``/``description``/``content`` (keyword) weighted 1.0x

    Args:
        query: Natural language query for semantic search.
        keywords: Optional explicit keywords to boost. If omitted, extracted
            from the query automatically.
        limit: Maximum number of results (default 10).
        tool_context: ADK tool context for tenant scoping.

    Returns:
        A HybridSearchSuccess with matched documents, or a HybridSearchError.

    Use after calling this tool: emit_checkpoint describing what patterns
    were matched and the distribution of results.
    """
    try:
        embedding = await _generate_query_embedding(query)
    except Exception as exc:
        return HybridSearchError(error=f"Embedding generation failed: {exc}")

    extracted_keywords = keywords or [w for w in query.split() if len(w) > 2]

    # Tenant scoping — normally AmbientContextPlugin injects this for LLM-
    # initiated MCP calls, but this tool opens its own session internally.
    tenant_id = tool_context.state.get(SessionState.TENANT_ID) if tool_context else None

    vector_search_stage: dict[str, Any] = {
        "$vectorSearch": {
            "index": "vector_search_index",
            "queryVector": embedding,
            "path": "embedding",
            "numCandidates": 100,
            "limit": 20,
        }
    }
    if tenant_id:
        vector_search_stage["$vectorSearch"]["preFilter"] = {
            "tenantId": {"$oid": tenant_id},
        }

    text_search_stage: dict[str, Any] = {
        "$search": {
            "index": "text_search_index",
            "text": {
                "query": " ".join(extracted_keywords),
                "path": ["name", "description", "content"],
            },
        }
    }
    if tenant_id:
        text_search_stage["$search"]["filter"] = {
            "tenantId": {"$oid": tenant_id},
        }

    pipeline: list[dict[str, Any]] = [
        {
            "$rankFusion": {
                "input": {
                    "pipelines": [
                        vector_search_stage,
                        text_search_stage,
                    ]
                },
                "rankFusion": {
                    "weights": {"0": 1.5, "1": 1.0},
                    "normalization": "minmax",
                },
            }
        },
        {"$limit": limit},
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "description": 1,
                "status": 1,
                "tags": 1,
                "metadata": 1,
                "score": {"$meta": "rankFusionScore"},
            }
        },
    ]

    try:
        params = StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri,
                "MDB_MCP_READ_ONLY": "true",
            },
        )
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(
                "aggregate",
                {
                    "collection": "memory_nodes",
                    "database": Database.CANON,
                    "pipeline": pipeline,
                },
            )

        if result.isError:
            for item in result.content:
                if isinstance(item, TextContent):
                    return HybridSearchError(
                        error=f"MongoDB MCP aggregate failed: {item.text}"
                    )
            return HybridSearchError(
                error="MongoDB MCP aggregate failed (unknown response)"
            )

        # Parse the result content into documents.
        docs: list[dict[str, Any]] = []
        for item in result.content:
            if not isinstance(item, TextContent) or not item.text:
                continue
            try:
                parsed = json.loads(item.text)
                if isinstance(parsed, list):
                    docs.extend(parsed)
                else:
                    docs.append(parsed)
            except json.JSONDecodeError:
                continue

        return HybridSearchSuccess(
            results=docs,
            count=len(docs),
            query=query,
        )
    except Exception as exc:
        return HybridSearchError(error=f"Hybrid search failed: {exc}")


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
hybrid_search_tool = FunctionTool(func=hybrid_search)
emit_checkpoint_tool = FunctionTool(func=emit_checkpoint)
