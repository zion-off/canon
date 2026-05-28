"""Shared MongoDB McpToolset — the LLM-facing database surface.

Provides a singleton McpToolset filtered to `find` and `count` — the only
database operations where LLM intent maps cleanly to a query shape. Every
call is intercepted by AmbientContextPlugin, which injects tenantId,
database, and EJSON wrapping.

All complex operations (aggregate pipelines, inserts, updates) live in
FunctionTools that call through session_provider — the LLM never touches
pipeline JSON or write operations.
"""

from __future__ import annotations

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams

from src.mcp.session_provider import get_mcp_params

_mongo_toolset: McpToolset | None = None


def get_mongo_toolset() -> McpToolset:
    """Return the shared write-capable MongoDB McpToolset singleton.

    Filtered to `find` and `count` — the LLM-level surface. All other
    operations (aggregate, insertOne, updateMany) are owned by FunctionTools
    through session_provider.
    """
    global _mongo_toolset
    if _mongo_toolset is None:
        _mongo_toolset = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=get_mcp_params(),
            ),
            tool_filter=["find", "count"],
        )
    return _mongo_toolset


async def close_mongo_toolset() -> None:
    """Close the shared McpToolset's underlying MCP subprocess connection."""
    global _mongo_toolset
    if _mongo_toolset is not None:
        await _mongo_toolset.close()
        _mongo_toolset = None
