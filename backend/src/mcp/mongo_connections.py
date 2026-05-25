"""Persistent MongoDB MCP subprocess connections.

Provides a shared, long-lived read-only MCP session for operations
that bypass the ADK agent tool chain (e.g., hybrid_search which
manually constructs its own aggregate pipeline). Also serves as the
single source of truth for MongoDB MCP server connection parameters.

Lifecycle is managed by the application lifespan:
    startup() → open subprocess + initialize session
    shutdown() → close session + terminate subprocess
"""

from __future__ import annotations

from typing import Any

from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp import ClientSession
from src.config import settings

_READ_PARAMS: StdioServerParameters | None = None
_WRITE_PARAMS: StdioServerParameters | None = None
_READ_SESSION: ClientSession | None = None

# Must hold references to the async context managers so they don't
# finalize (and close transports) when __aexit__ runs at shutdown.
_read_ctx: Any = None
_session_ctx: Any = None


def get_read_params() -> StdioServerParameters:
    """Return the canonical read-only MongoDB MCP server parameters."""
    global _READ_PARAMS
    if _READ_PARAMS is None:
        _READ_PARAMS = StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri,
                "MDB_MCP_READ_ONLY": "true",
            },
        )
    return _READ_PARAMS


def get_write_params() -> StdioServerParameters:
    """Return the canonical write-capable MongoDB MCP server parameters."""
    global _WRITE_PARAMS
    if _WRITE_PARAMS is None:
        _WRITE_PARAMS = StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri,
            },
        )
    return _WRITE_PARAMS


async def startup() -> None:
    """Start the persistent read-only MCP subprocess and initialize the session."""
    global _read_ctx, _session_ctx, _READ_SESSION

    params = get_read_params()
    _read_ctx = stdio_client(params)
    read, write = await _read_ctx.__aenter__()
    _session_ctx = ClientSession(read, write)
    session = await _session_ctx.__aenter__()
    await session.initialize()
    _READ_SESSION = session


async def shutdown() -> None:
    """Close the persistent session and terminate the subprocess."""
    global _READ_SESSION, _session_ctx, _read_ctx

    if _session_ctx is not None:
        await _session_ctx.__aexit__(None, None, None)
        _session_ctx = None

    if _read_ctx is not None:
        await _read_ctx.__aexit__(None, None, None)
        _read_ctx = None

    _READ_SESSION = None


async def call_aggregate(collection: str, pipeline: list[dict[str, Any]]) -> Any:
    """Execute an aggregate pipeline against the shared read-only session.

    Args:
        collection: Target MongoDB collection name.
        pipeline: Aggregate pipeline stages.

    Returns:
        Raw CallToolResult from the MCP server.

    Raises:
        RuntimeError: If the session hasn't been started.
    """
    if _READ_SESSION is None:
        raise RuntimeError("MongoMCP read session not started")

    return await _READ_SESSION.call_tool(
        "aggregate",
        {
            "collection": collection,
            "database": "canon",
            "pipeline": pipeline,
        },
    )
