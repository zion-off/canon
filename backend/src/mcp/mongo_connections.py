"""Persistent MongoDB MCP subprocess connections.

Provides a shared, long-lived read-only MCP session for operations
that bypass the ADK agent tool chain (e.g., hybrid_search which
manually constructs its own aggregate pipeline). Also serves as the
single source of truth for MongoDB MCP server connection parameters.

Lifecycle is managed by the application lifespan:
    startup() → open subprocess + initialize session
    shutdown() → drain in-flight ops → close session + terminate subprocess
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from src.config import settings


class _ConnectionState:
    """Module-level singleton for MongoDB MCP connection state."""

    read_params: StdioServerParameters | None = None
    write_params: StdioServerParameters | None = None
    read_session: ClientSession | None = None
    # Must hold references to the async context managers so they don't
    # finalize (and close transports) when __aexit__ runs at shutdown.
    read_ctx: Any = None
    session_ctx: Any = None
    _shutting_down = asyncio.Event()
    _in_flight = 0
    _lock = asyncio.Lock()
    _drained = asyncio.Event()


def get_read_params() -> StdioServerParameters:
    """Return the canonical read-only MongoDB MCP server parameters."""
    if _ConnectionState.read_params is None:
        _ConnectionState.read_params = StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri,
                "MDB_MCP_READ_ONLY": "true",
            },
        )
    return _ConnectionState.read_params


def get_write_params() -> StdioServerParameters:
    """Return the canonical write-capable MongoDB MCP server parameters."""
    if _ConnectionState.write_params is None:
        _ConnectionState.write_params = StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri,
            },
        )
    return _ConnectionState.write_params


async def startup() -> None:
    """Start the persistent read-only MCP subprocess and initialize the session."""
    log = logging.getLogger(__name__)
    log.info("mongo_connections: starting read-only MCP subprocess")
    _ConnectionState._shutting_down.clear()
    _ConnectionState._drained.clear()
    _ConnectionState._in_flight = 0
    params = get_read_params()
    _ConnectionState.read_ctx = stdio_client(params)
    read, write = await _ConnectionState.read_ctx.__aenter__()
    _ConnectionState.session_ctx = ClientSession(read, write)
    session = await _ConnectionState.session_ctx.__aenter__()
    await session.initialize()
    _ConnectionState.read_session = session
    log.info("mongo_connections: read-only MCP session initialized")


async def shutdown() -> None:
    """Close the persistent session and terminate the subprocess.

    Signals in-flight operations to stop and drains them before teardown
    to avoid ASGI errors during hot reload.
    """
    log = logging.getLogger(__name__)
    log.info("mongo_connections: shutting down MCP subprocess")
    _ConnectionState._shutting_down.set()

    async with _ConnectionState._lock:
        if _ConnectionState._in_flight > 0:
            log.info(
                "mongo_connections: draining %d in-flight operation(s)",
                _ConnectionState._in_flight,
            )
            try:
                await asyncio.wait_for(_ConnectionState._drained.wait(), timeout=5.0)
            except TimeoutError:
                log.warning(
                    "mongo_connections: drain timed out with %d in-flight",
                    _ConnectionState._in_flight,
                )

    if _ConnectionState.session_ctx is not None:
        await _ConnectionState.session_ctx.__aexit__(None, None, None)
        _ConnectionState.session_ctx = None

    if _ConnectionState.read_ctx is not None:
        await _ConnectionState.read_ctx.__aexit__(None, None, None)
        _ConnectionState.read_ctx = None

    _ConnectionState.read_session = None
    log.info("mongo_connections: MCP subprocess shut down")


async def _reconnect_read_session() -> ClientSession:
    """Tear down the existing read session/transport and start a fresh one."""
    log = logging.getLogger(__name__)
    log.warning("mongo_connections: read session lost, reconnecting")

    if _ConnectionState._shutting_down.is_set():
        raise RuntimeError("MongoMCP session is shutting down")

    if _ConnectionState.session_ctx is not None:
        with contextlib.suppress(Exception):
            await _ConnectionState.session_ctx.__aexit__(None, None, None)
        _ConnectionState.session_ctx = None

    if _ConnectionState.read_ctx is not None:
        with contextlib.suppress(Exception):
            await _ConnectionState.read_ctx.__aexit__(None, None, None)
        _ConnectionState.read_ctx = None

    _ConnectionState.read_session = None

    params = get_read_params()
    _ConnectionState.read_ctx = stdio_client(params)
    read, write = await _ConnectionState.read_ctx.__aenter__()
    _ConnectionState.session_ctx = ClientSession(read, write)
    session = await _ConnectionState.session_ctx.__aenter__()
    await session.initialize()
    _ConnectionState.read_session = session
    log.info("mongo_connections: read session reconnected")
    return session


async def call_aggregate(collection: str, pipeline: list[dict[str, Any]]) -> Any:
    """Execute an aggregate pipeline against the shared read-only session.

    If the underlying subprocess has died, transparently reconnects before
    retrying once.

    Args:
        collection: Target MongoDB collection name.
        pipeline: Aggregate pipeline stages.

    Returns:
        Raw CallToolResult from the MCP server.

    Raises:
        RuntimeError: If the session cannot be started or reconnected.
    """
    if _ConnectionState._shutting_down.is_set():
        raise RuntimeError("MongoMCP session is shutting down")

    session = _ConnectionState.read_session
    if session is None:
        raise RuntimeError("MongoMCP read session not started")

    async with _ConnectionState._lock:
        _ConnectionState._in_flight += 1

    log = logging.getLogger(__name__)
    log.debug(
        "mongo_connections: calling aggregate | collection=%s pipeline_stages=%d",
        collection,
        len(pipeline),
    )

    try:
        for attempt in range(2):
            try:
                return await session.call_tool(
                    "aggregate",
                    {
                        "collection": collection,
                        "database": "canon",
                        "pipeline": pipeline,
                    },
                )
            except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                if attempt == 0:
                    log.warning(
                        "mongo_connections: aggregate failed (attempt 1/2) | error=%s",
                        exc,
                    )
                    session = await _reconnect_read_session()
                else:
                    raise RuntimeError(
                        f"MongoMCP aggregate failed after reconnect: {exc}"
                    ) from exc
    finally:
        async with _ConnectionState._lock:
            _ConnectionState._in_flight -= 1
            if _ConnectionState._in_flight == 0:
                _ConnectionState._drained.set()
