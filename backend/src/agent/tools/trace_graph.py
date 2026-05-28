"""Trace graph tool — graph traversal as a FunctionTool.

The LLM emits intent ("trace these entity IDs"), the harness builds the exact
$graphLookup pipeline in Python and executes it through session_provider.
The LLM never sees a pipeline stage.
"""

import logging
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.agent.constants import Collections, Database, SessionState
from src.agent.models import TraceGraphError, TraceGraphResult, TraceGraphSuccess
from src.mcp.provider import call_tool
from src.mcp.response import (
    extract_mcp_error_text,
    mcp_result_is_error,
    parse_mcp_docs,
)

logger = logging.getLogger(__name__)


def _unwrap_oids(obj: Any) -> Any:
    """Recursively convert EJSON $oid dicts to plain hex strings.

    The LLM should see clean hex strings, not EJSON wrapping —
    consistent with how SearchResultItem.unwrap_oid handles _id fields
    in hybrid search results.
    """
    if isinstance(obj, dict):
        if list(obj.keys()) == ["$oid"] and isinstance(obj["$oid"], str):
            return obj["$oid"]
        return {k: _unwrap_oids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_unwrap_oids(item) for item in obj]
    return obj


def _enrich_trace_result(
    docs: list[dict[str, Any]],
    max_depth: int,
    entity_count: int,
) -> TraceGraphSuccess:
    """Populate note/next_actions based on graph traversal results."""
    total_connected = sum(len(node.get("connected", [])) for node in docs)

    if total_connected == 0:
        return TraceGraphSuccess(
            nodes=docs,
            count=len(docs),
            note="Nodes found but none have relationships to other memories. "
            "They are isolated in the graph — no dependencies, ownership "
            "links, or supersession chains connect them to anything else.",
            next_actions=[
                "Report isolated nodes to the orchestrator with names and statuses",
                "If the orchestrator needs graph context, try semantic_retriever "
                "with broader terms to find connected alternatives",
            ],
        )

    has_supersession = any(
        node.get("supersedes") or node.get("supersededBy") for node in docs
    )

    if has_supersession:
        return TraceGraphSuccess(
            nodes=docs,
            count=len(docs),
            note=f"Found {len(docs)} nodes with {total_connected} connected "
            f"memories across up to {max_depth} hops. Supersession chains "
            "detected — some nodes have replaced or been replaced by others.",
            next_actions=[
                "Identify active supersession targets — they carry the most authority",
                "Surface dependency direction: which node depends on which",
                "Report ownership boundaries and impact radius to the orchestrator",
            ],
        )

    return TraceGraphSuccess(
        nodes=docs,
        count=len(docs),
        note=f"Found {len(docs)} nodes with {total_connected} connected "
        f"memories across up to {max_depth} hops.",
        next_actions=[
            "Surface dependency and ownership relationships to the orchestrator",
            "Note any patterns: clusters of related nodes, shared ownership, "
            "or temporal ordering (created/updated sequences)",
        ],
    )


async def trace_graph(
    entity_ids: list[str],
    max_depth: int = 2,
    tool_context: ToolContext | None = None,
) -> TraceGraphResult:
    """Trace relationship paths from memory node IDs via $graphLookup.

    Discovers connected nodes, dependency chains, supersession chains,
    and ownership structures. The orchestrator provides entity IDs from
    search results; this tool returns the connected graph.

    Args:
        entity_ids: Hex-string memory node IDs to start traversal from.
        max_depth: Maximum graph traversal depth. Defaults to 2.
        tool_context: The ADK tool context, providing session state
            (tenant ID). Injected by the framework.

    Returns:
        TraceGraphSuccess with nodes + connected graph, or TraceGraphError
        on failure.
    """
    log = logging.getLogger(__name__)

    if not entity_ids:
        return TraceGraphError(
            error="No entity IDs provided for graph traversal.",
            hint="The orchestrator must provide at least one memory node ID",
            retry="Provide entity IDs from hybrid_search results or a prior find call",
        )

    tenant_id = tool_context.state.get(SessionState.TENANT_ID) if tool_context else None
    oid_values = [{"$oid": oid} for oid in entity_ids]

    pipeline: list[dict[str, Any]] = [
        {
            "$match": {"_id": {"$in": oid_values}},
        },
        {
            "$graphLookup": {
                "from": Collections.MEMORY_NODES,
                "startWith": "$relatedEntityIds",
                "connectFromField": "relatedEntityIds",
                "connectToField": "_id",
                "as": "connected",
                "maxDepth": min(max_depth, 3),
                "depthField": "hops",
            },
        },
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "description": 1,
                "status": 1,
                "tags": 1,
                "metadata": 1,
                "relatedEntityIds": 1,
                "supersedes": 1,
                "supersededBy": 1,
                "connected._id": 1,
                "connected.name": 1,
                "connected.description": 1,
                "connected.status": 1,
                "connected.tags": 1,
                "connected.hops": 1,
                "connected.relatedEntityIds": 1,
            },
        },
    ]

    if tenant_id:
        gl = pipeline[1]["$graphLookup"]
        gl["restrictSearchWithMatch"] = {"tenantId": {"$oid": tenant_id}}
        pipeline[0]["$match"]["tenantId"] = {"$oid": tenant_id}

    log.info(
        "trace_graph: executing | entity_count=%d max_depth=%d",
        len(entity_ids),
        max_depth,
    )

    try:
        result = await call_tool(
            "aggregate",
            {
                "collection": Collections.MEMORY_NODES,
                "database": Database.CANON,
                "pipeline": pipeline,
            },
        )
    except Exception as exc:
        log.warning("trace_graph: MCP call failed | error=%s", exc)
        return TraceGraphError(
            error=f"MongoDB MCP aggregate failed: {exc}",
            hint="MCP subprocess unavailable",
            retry="Retry once. If persistent, surface the error.",
        )

    if mcp_result_is_error(result):
        error_text = extract_mcp_error_text(result)
        log.warning(
            "trace_graph: aggregate returned error | ids=%s error=%s",
            entity_ids,
            error_text,
        )
        return TraceGraphError(
            error=f"MongoDB MCP aggregate failed: {error_text}",
            hint="MongoDB query returned an error",
            retry="Verify entity IDs are valid 24-char hex strings",
        )

    docs = parse_mcp_docs(result.content)

    if not docs:
        log.info("trace_graph: $graphLookup returned empty, trying direct find")
        try:
            find_result = await call_tool(
                "find",
                {
                    "collection": Collections.MEMORY_NODES,
                    "database": Database.CANON,
                    "filter": {"_id": {"$in": oid_values}},
                },
            )
        except Exception as exc:
            log.warning("trace_graph: fallback find failed | error=%s", exc)
            return TraceGraphError(
                error=f"Graph traversal returned no results and fallback find failed: {exc}",
                hint="The requested memory nodes may not exist",
                retry="Verify entity IDs are valid 24-char hex strings from actual query results",
            )

        if not mcp_result_is_error(find_result):
            docs = parse_mcp_docs(find_result.content)

    docs = _unwrap_oids(docs)

    if not docs:
        log.info("trace_graph: no results for entity_ids=%s", entity_ids[:5])
        return TraceGraphSuccess(
            nodes=[],
            count=0,
            note="No nodes found for the provided entity IDs",
            next_actions=[
                "Verify entity IDs from search results",
                "Try name-based lookup with find tool",
            ],
        )

    return _enrich_trace_result(
        docs=docs,
        max_depth=max_depth,
        entity_count=len(entity_ids),
    )


trace_graph_tool = FunctionTool(func=trace_graph)
