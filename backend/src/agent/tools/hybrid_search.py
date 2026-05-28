"""Hybrid search tool for Canon agents.

Searches memory nodes via hybrid semantic and keyword search using
the MongoDB MCP server.
"""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from mcp.types import TextContent

from src.agent.agent_platform import CanonModel
from src.agent.constants import SessionState
from src.agent.models import (
    HybridSearchError,
    HybridSearchResult,
    HybridSearchSuccess,
    SearchResultItem,
)
from src.config import settings
from src.mcp.session_provider import call_tool, parse_mcp_docs


def build_embedding_text(doc) -> str:
    """Build a retrieval-optimized semantic representation of a memory node."""
    from src.agent.models import MemoryNodeInput

    if not isinstance(doc, MemoryNodeInput):
        lines: list[str] = []
        if isinstance(doc, dict):
            header = doc.get("name", "")
            if doc.get("status"):
                header += f" [{doc['status']}]"
            lines.append(header)
            if doc.get("description"):
                lines.append(str(doc["description"]))
            if doc.get("content"):
                lines.append(str(doc["content"])[:1500])
            if doc.get("tags"):
                lines.append("Tags: " + ", ".join(doc["tags"]))
        return "\n".join(filter(None, lines))

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

    Performs semantic vector search and full-text keyword search against
    the memory node collection, then fuses results into a ranked list.

    Args:
        query: The natural-language search query for semantic retrieval.
        keywords: Optional explicit keywords to boost in the full-text
            search component. Defaults to None.
        limit: Maximum number of results to return. Defaults to 10.
        tool_context: The ADK tool context, providing session state
            (tenant ID, user ID). Injected by the framework. Defaults to
            None (allows standalone use outside ADK).

    Returns:
        A HybridSearchResult containing a list of search hits, each with
        id, name, description, status, tags, score, match_type, and
        optionally metadata and highlight.
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
    log.info(
        "hybrid_search: embedding generated | query=%.80s dims=%d",
        query,
        len(embedding),
    )

    extracted_keywords = keywords or [w for w in query.split() if len(w) > 2]

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

    text_search_stage: dict[str, Any] = {
        "$search": {
            "index": "text_search_index",
            "text": {
                "query": " ".join(extracted_keywords),
                "path": ["name", "description", "content"],
            },
        }
    }

    pipeline: list[dict[str, Any]] = [
        {
            "$rankFusion": {
                "input": {
                    "pipelines": {
                        "vector": [vector_search_stage],
                        "text": [text_search_stage, {"$limit": 20}],
                    }
                },
                "combination": {
                    "weights": {"vector": 1.5, "text": 1.0},
                },
            }
        },
    ]

    if tenant_id:
        pipeline.append({"$match": {"tenantId": {"$oid": tenant_id}}})

    pipeline += [
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

    log.info(
        "hybrid_search: executing | query=%.120s keywords=%s limit=%d",
        query,
        extracted_keywords[:5],
        limit,
    )

    try:
        result = await call_tool(
            "aggregate",
            {
                "collection": "memory_nodes",
                "database": "canon",
                "pipeline": pipeline,
            },
        )

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

        docs: list[dict[str, Any]] = parse_mcp_docs(result.content)

        results = [SearchResultItem.model_validate(d) for d in docs]
        top_names = [r.name for r in results[:5]]

        log.info(
            "hybrid_search: done | query=%.120s count=%d top=[%s]",
            query,
            len(results),
            ", ".join(top_names) if top_names else "(none)",
        )

        return _enrich_search_result(
            HybridSearchSuccess(
                results=results,
                count=len(results),
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


hybrid_search_tool = FunctionTool(func=hybrid_search)
