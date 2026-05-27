from __future__ import annotations

import logging

from google.adk.agents import Agent
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.tool_context import ToolContext

from src.agent.agent_platform import CanonModel
from src.agent.constants import AgentName
from src.agent.tools.emit_checkpoint import emit_checkpoint_tool
from src.config import settings
from src.mcp.mongo_connections import get_read_params

logger = logging.getLogger(__name__)

GRAPH_EXPLORER_INSTRUCTION = """\
You are Canon's spatial reasoning — you map the organizational impact radius
of memories by traversing their relationship edges in MongoDB.

When the orchestrator gives you memory IDs, it wants to know: what connects
to these memories? What is active and constraining? What teams, services, or
decisions are in the blast radius?

## Input Contract

You receive one or more memory IDs (hex strings) from the orchestrator.
The orchestrator has already resolved names to IDs via semantic_retriever.
Do NOT accept names unless using the Name Fallback below.

## Query Protocol

Budget: 2 MCP tool calls total.

### Step 1 — Graph Traversal

Use ``aggregate`` on collection ``memory_nodes`` with this exact pipeline.
Do NOT add, remove, or modify any stages. Do NOT use $vectorSearch or $search.

```json
[
  {
    "$match": { "_id": { "$in": [{ "$oid": "<id1>" }, { "$oid": "<id2>" }] } }
  },
  {
    "$graphLookup": {
      "from": "memory_nodes",
      "startWith": "$relatedEntityIds",
      "connectFromField": "relatedEntityIds",
      "connectToField": "_id",
      "as": "connected",
      "maxDepth": 2,
      "depthField": "hops"
    }
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
      "connected.relatedEntityIds": 1
    }
  }
]
```

Notes on the pipeline:

- Do NOT include ``database`` or ``tenantId`` — those are injected
  automatically.
- Memory IDs must be formatted as {"$oid": "<hex>"}.
- maxDepth of 2 is the default. Only increase if explicitly requested.

### Step 2 — Fallback (only if Step 1 returns empty or errors)

If Step 1 returns no results and you have remaining budget, try a direct
``find`` on collection ``memory_nodes`` with the IDs:

```json
{
  "collection": "memory_nodes",
  "filter": { "_id": { "$in": [{ "$oid": "<id1>" }, { "$oid": "<id2>" }] } }
}
```

This confirms whether the memories exist at all.

## Output Structure

Surface what matters most first. For each area where you found relevant nodes,
report:

- **Active and in-progress nodes** — what is live and constraining right now
- **Supersession chains** — what replaced what, and why
- **Ownership and dependent systems** — who owns this, what depends on it
- **Historical context** — deprecated or completed nodes

The orchestrator synthesizes — you discover and report the graph.

## Error Handling

- If the MCP tool returns an error, report it verbatim. Do NOT retry with
  the same query.
- Never fabricate IDs or invent connections not present in results.

## Name Fallback (rare)

If the orchestrator provides a name instead of an ID (shouldn't happen
normally), use find to resolve it:

```json
{
  "collection": "memory_nodes",
  "filter": { "name": { "$regex": "^<name>$", "$options": "i" } },
  "projection": { "_id": 1, "name": 1 }
}
```
"""


async def graph_explorer_after_tool(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext,
    tool_response,
):
    """Observe graph_explorer tool responses for error patterns."""
    response_str = str(tool_response) if tool_response else ""
    if "error" in response_str.lower() or "Error" in response_str:
        logger.warning(
            "graph_explorer tool '%s' returned error-like response: %.200s",
            tool.name,
            response_str,
        )
    return None  # Don't modify the response


_graph_explorer: Agent | None = None
_read_toolset: McpToolset | None = None


def _build_mongo_read_toolset() -> McpToolset:
    global _read_toolset
    if _read_toolset is not None:
        return _read_toolset
    _read_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=get_read_params(),
        ),
        tool_filter=["find", "aggregate", "count"],
    )
    return _read_toolset


def get_mongo_read_toolset() -> McpToolset:
    """Return the singleton read-only MongoDB MCP toolset.

    Exposed for lifecycle management — callers can close the underlying
    subprocess connection via ``await toolset.close()``.
    """
    return _build_mongo_read_toolset()


def get_graph_explorer() -> Agent:
    """Return the singleton graph_explorer agent.

    Lazy-initialises on first call so the MCP toolset is primed on demand.
    """
    global _graph_explorer
    if _graph_explorer is None:
        _graph_explorer = Agent(
            name=AgentName.GRAPH_EXPLORER,
            model=CanonModel.create(settings.fast_model),
            description=(
                "Navigates relationships between memories using MongoDB. "
                "Accepts entity IDs (hex strings) only — never names. "
                "Returns connected context and relationship paths."
            ),
            instruction=GRAPH_EXPLORER_INSTRUCTION,
            tools=[_build_mongo_read_toolset(), emit_checkpoint_tool],
            output_key="graph_results",
            after_tool_callback=graph_explorer_after_tool,
        )
    return _graph_explorer
