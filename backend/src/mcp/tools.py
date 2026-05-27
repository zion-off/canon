"""ADK agent tools for the Canon memory graph.

Provides tools that agents use for hybrid search, memory persistence,
and reasoning checkpoints.

- hybrid_search: generates embeddings and executes $rankFusion via the
  shared read-only MCP session — the LLM never handles raw vectors.
- canonize_node: validates, embeds, and persists a memory node via Beanie,
  wiring bidirectional edges and cascading supersession in one operation.
- emit_checkpoint: records reasoning milestones for the Reasoning Feed.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from beanie.odm.fields import PydanticObjectId
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from mcp.types import TextContent

from src.config import settings
from src.mcp.agent_platform import CanonModel
from src.mcp.constants import SessionState, TempState
from src.mcp.models import (
    CanonizeError,
    CanonizeResult,
    CanonizeSuccess,
    HybridSearchError,
    HybridSearchResult,
    HybridSearchSuccess,
    MemoryNodeInput,
    SearchResultItem,
)
from src.mcp.mongo_connections import call_aggregate
from src.models.documents import MemoryNodeDocument

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


def _enrich_search_result(
    result: HybridSearchSuccess, limit: int = 10
) -> HybridSearchSuccess:
    """Populate note/next_actions based on result characteristics."""
    if result.count == 0:
        result.note = "No results — try broader terms or different keywords"
        result.next_actions = [
            "Retry with broader query",
            "Report no relevant context found",
        ]
    elif result.count < 3:
        result.note = "Few results — knowledge may be sparse on this topic"
        result.next_actions = [
            "Trace relationships from found IDs via graph_explorer",
        ]
    elif result.count >= limit:
        result.note = "Results capped at limit — most relevant are first"
        result.next_actions = ["Focus on top results for entity IDs to trace"]
    else:
        result.next_actions = [
            "Trace relationships from found IDs via graph_explorer",
        ]
    return result


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
        embedding = await CanonModel.embed(
            query, task_type="RETRIEVAL_QUERY", model=settings.embedding_model
        )
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "hybrid_search: embedding failed | query=%.80s error=%s",
            query,
            exc,
        )
        return HybridSearchError(
            error=f"Embedding generation failed: {exc}",
            hint="Embedding model unavailable",
            retry="Wait and retry. If persistent, surface the error.",
        )

    log = logging.getLogger(__name__)
    log.debug(
        "hybrid_search: embedding generated | query=%.80s dims=%d",
        query,
        len(embedding),
    )

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

    text_query = {
        "text": {
            "query": " ".join(extracted_keywords),
            "path": ["name", "description", "content"],
        }
    }
    if tenant_id:
        text_search_stage: dict[str, Any] = {
            "$search": {
                "index": "text_search_index",
                "compound": {
                    "must": [text_query],
                    "filter": [
                        {
                            "equals": {
                                "path": "tenantId",
                                "value": {"$oid": tenant_id},
                            }
                        }
                    ],
                },
            }
        }
    else:
        text_search_stage: dict[str, Any] = {
            "$search": {
                "index": "text_search_index",
                **text_query,
            }
        }

    pipeline: list[dict[str, Any]] = [
        {
            "$rankFusion": {
                "input": {
                    "pipelines": {
                        "vector": [vector_search_stage],
                        "text": [text_search_stage],
                    }
                },
                "combination": {
                    "weights": {"vector": 1.5, "text": 1.0},
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
            }
        },
    ]

    try:
        result = await call_aggregate("memory_nodes", pipeline)

        if result.isError:
            for item in result.content:
                if isinstance(item, TextContent):
                    log.warning(
                        "hybrid_search: aggregate returned error | query=%.80s error=%s",
                        query,
                        item.text,
                    )
                    return HybridSearchError(
                        error=f"MongoDB MCP aggregate failed: {item.text}",
                        hint="MongoDB query returned an error",
                        retry="Simplify pipeline or try different query",
                    )
            log.warning(
                "hybrid_search: aggregate returned error (no content) | query=%.80s",
                query,
            )
            return HybridSearchError(
                error="MongoDB MCP aggregate failed (unknown response)",
                hint="MongoDB query returned an error",
                retry="Simplify pipeline or try different query",
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

        return _enrich_search_result(
            HybridSearchSuccess(
                results=[SearchResultItem.model_validate(d) for d in docs],
                count=len(docs),
                query=query,
            ),
            limit,
        )
    except Exception as exc:
        log.warning(
            "hybrid_search: failed | query=%.80s error=%s",
            query,
            exc,
        )
        return HybridSearchError(
            error=f"Hybrid search failed: {exc}",
            hint="Unexpected failure",
            retry="Retry once. If persistent, continue without results.",
        )


# ─── Core Agent Tools ────────────────────────────────────────────────────────


async def canonize_node(
    document: MemoryNodeInput,
    rationale: str,
    reverse_link_ids: list[str],
    tool_context: ToolContext,
) -> CanonizeResult:
    """Persist an observation as a structured memory node in the knowledge graph.

    Validates the document, generates an embedding, inserts the node, wires
    bidirectional edges on related existing nodes, and cascades supersession
    if this node replaces a predecessor — all in one atomic operation.

    Do NOT set embeddingText, embedding, createdAt, updatedAt, or tenantId —
    those are injected by this tool.

    Args:
        document: Memory node fields — name (str), description (str),
            content (str), status (active|deprecated|in_progress|resolved|completed),
            tags (list[str]), metadata (dict), and optionally relatedEntityIds
            (list of hex IDs to link from this node) and supersedes (hex ID of
            the node this one replaces).
        rationale: Why this node should exist.
        reverse_link_ids: Hex IDs of existing nodes whose relatedEntityIds
            should be updated to include this new node (reverse edges).
        tool_context: ADK tool context — injected automatically, do not pass.

    Returns:
        CanonizeSuccess with node_id and relationships_formed, or CanonizeError.
    """
    log = logging.getLogger(__name__)
    if isinstance(document, dict):
        try:
            doc = MemoryNodeInput.model_validate(document)
        except Exception as exc:
            log.warning("canonize_node: validation failed | error=%s", exc)
            return CanonizeError(
                error=f"Invalid document: {exc}",
                hint="Document schema invalid",
                retry="Check required fields: name, description, content, status",
            )
    else:
        doc = document

    tenant_id_str = tool_context.state.get(SessionState.TENANT_ID)
    if not tenant_id_str:
        return CanonizeError(
            error="No tenant context in session state.",
            hint="Missing tenant context",
        )

    try:
        tenant_oid = PydanticObjectId(tenant_id_str)
        related_entity_oids = [PydanticObjectId(rid) for rid in doc.related_entity_ids]
        related_existing_oids = [PydanticObjectId(rid) for rid in reverse_link_ids]
    except Exception as exc:
        return CanonizeError(
            error=f"Invalid ObjectId: {exc}",
            hint="Malformed ID",
            retry="Verify IDs are 24-char hex from actual query results",
        )

    supersedes_oid: PydanticObjectId | None = None
    if doc.supersedes:
        try:
            supersedes_oid = PydanticObjectId(doc.supersedes)
        except Exception as exc:
            return CanonizeError(
                error=f"Invalid ObjectId in supersedes: {exc}",
                hint="Malformed ID",
                retry="Verify IDs are 24-char hex from actual query results",
            )

    now = datetime.now(tz=UTC)
    embedding_text = build_embedding_text(doc)
    try:
        embedding = await CanonModel.embed(
            embedding_text,
            task_type="RETRIEVAL_DOCUMENT",
            model=settings.embedding_model,
        )
    except Exception as exc:
        log.warning("canonize_node: embedding failed | error=%s", exc)
        return CanonizeError(
            error=f"Embedding generation failed: {exc}",
            hint="Embedding model unavailable",
            retry="Wait and retry",
        )

    node_doc = MemoryNodeDocument(
        tenantId=tenant_oid,
        name=doc.name,
        description=doc.description,
        content=doc.content,
        status=doc.status,
        tags=doc.tags,
        metadata=doc.metadata,
        relatedEntityIds=related_entity_oids,
        supersedes=supersedes_oid,
        embeddingText=embedding_text,
        embedding=embedding,
        createdAt=now,
        updatedAt=now,
    )
    try:
        await node_doc.insert()
    except Exception as exc:
        if "duplicate key" in str(exc).lower():
            return CanonizeError(
                error=f"A node named '{doc.name}' already exists for this tenant.",
                hint="A memory with this name already exists",
                retry="Use different name or supersede existing. Retrieve it first.",
            )
        log.warning("canonize_node: insert failed | name=%s error=%s", doc.name, exc)
        return CanonizeError(
            error=f"Insert failed: {exc}",
            hint="Database write failed",
            retry="Retry once. If persistent, surface the error.",
        )

    new_id = node_doc.id
    relationships_formed = 0

    # Update reverse edges on related existing nodes.
    if related_existing_oids:
        await MemoryNodeDocument.find(
            {"_id": {"$in": related_existing_oids}, "tenantId": tenant_oid}
        ).update_many(
            {"$addToSet": {"relatedEntityIds": new_id}, "$set": {"updatedAt": now}}
        )
        relationships_formed += len(related_existing_oids)

    # Cascade supersession — mark predecessor as deprecated.
    if supersedes_oid:
        await MemoryNodeDocument.find(
            {"_id": supersedes_oid, "tenantId": tenant_oid}
        ).update_many(
            {"$set": {"supersededBy": new_id, "status": "deprecated", "updatedAt": now}}
        )
        relationships_formed += 1

    log.info(
        "canonize_node: written | name=%s node_id=%s relationships=%d rationale=%.80s",
        doc.name,
        new_id,
        relationships_formed,
        rationale,
    )
    return CanonizeSuccess(
        node_id=str(new_id),
        name=doc.name,
        relationships_formed=relationships_formed,
    )


async def emit_checkpoint(message: str, tool_context: ToolContext) -> dict[str, str]:
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
    logging.getLogger(__name__).info(
        "emit_checkpoint: agent=%s msg=%.120s",
        tool_context.agent_name,
        message,
    )
    return {"status": "ok", "message": message}


# ─── Tool Instances ──────────────────────────────────────────────────────────

canonize_node_tool = FunctionTool(func=canonize_node)
hybrid_search_tool = FunctionTool(func=hybrid_search)
emit_checkpoint_tool = FunctionTool(func=emit_checkpoint)
