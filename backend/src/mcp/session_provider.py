"""Persistent MongoDB MCP subprocess for programmatic (FunctionTool) access.

Provides a shared, long-lived write-capable MCP session for FunctionTools
that construct their own pipelines and documents — hybrid_search, trace_graph,
canonize_node. These tools own the query/document structure in Python; the MCP
server is purely a transport layer.

This is NOT the LLM-facing surface. That is the shared McpToolset in
src.agent.mongo_toolset, guarded by AmbientContextPlugin.

Lifecycle is managed by the application lifespan:
    startup() → open subprocess + initialize session
    shutdown() → drain in-flight ops → close session + terminate subprocess

Module-level convenience functions (startup, shutdown, call_tool) delegate
to a singleton SessionProvider instance. Tests can instantiate their own.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from typing import Any

from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp import ClientSession
from src.config import settings

logger = logging.getLogger(__name__)

_UNTRUSTED_CONTENT_RE = re.compile(
    r"<untrusted-user-data-[^>]+>(.*?)</untrusted-user-data-[^>]+>",
    re.DOTALL,
)


def parse_mcp_docs(content_items: list[Any]) -> list[dict[str, Any]]:
    """Extract documents from MCP CallToolResult content items.

    Handles TextContent with optional <untrusted-user-data> wrappers
    produced by the mongodb-mcp-server. Returns a flat list of dicts.
    """
    docs: list[dict[str, Any]] = []
    for item in content_items:
        raw = getattr(item, "text", "")
        if not raw:
            continue

        parsed = False
        for inner in _UNTRUSTED_CONTENT_RE.findall(raw):
            candidate = inner.strip()
            if not candidate:
                continue
            try:
                parsed_data = json.loads(candidate)
                docs.extend(parsed_data) if isinstance(
                    parsed_data, list
                ) else docs.append(parsed_data)
                parsed = True
                break
            except json.JSONDecodeError:
                pass
        if parsed:
            continue

        try:
            parsed_data = json.loads(raw)
            docs.extend(parsed_data) if isinstance(parsed_data, list) else docs.append(
                parsed_data
            )
        except json.JSONDecodeError:
            logger.debug(
                "parse_mcp_docs: skipping non-JSON content | raw=%.120s", raw[:120]
            )
    return docs


def get_mcp_params() -> StdioServerParameters:
    """Return the canonical write-capable MongoDB MCP server parameters.

    Used by both the lifespan-managed session and the shared McpToolset
    so both subprocesses share the same configuration.
    """
    return StdioServerParameters(
        command="npx",
        args=["-y", "mongodb-mcp-server"],
        env={
            "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri,
        },
    )


class SessionProvider:
    """Long-lived MCP subprocess session for programmatic tool calls.

    Manages the subprocess lifecycle, transparent reconnection on pipe
    breaks, draining in-flight operations on shutdown, and provides a
    single call_tool entrypoint for all FunctionTools.

    A module-level singleton (_provider) is used for the application lifespan.
    Tests can instantiate directly with ``async with SessionProvider() as sp:``
    to get an isolated subprocess.
    """

    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._read_ctx: Any = None
        self._session_ctx: Any = None
        self._shutting_down = asyncio.Event()
        self._in_flight = 0
        self._lock = asyncio.Lock()
        self._drained = asyncio.Event()

    async def start(self) -> None:
        """Start the MCP subprocess and initialize the session."""
        self._shutting_down.clear()
        self._drained.clear()
        self._in_flight = 0
        params = get_mcp_params()
        self._read_ctx = stdio_client(params)
        read, write = await self._read_ctx.__aenter__()
        self._session_ctx = ClientSession(read, write)
        session = await self._session_ctx.__aenter__()
        await session.initialize()
        self._session = session
        logger.info("session_provider: MCP session initialized")

    async def stop(self) -> None:
        """Close the session and terminate the subprocess.

        Signals in-flight operations to stop and drains them before
        teardown to avoid ASGI errors during hot reload.
        """
        logger.info("session_provider: shutting down MCP subprocess")
        self._shutting_down.set()

        async with self._lock:
            if self._in_flight > 0:
                logger.info(
                    "session_provider: draining %d in-flight operation(s)",
                    self._in_flight,
                )
                try:
                    await asyncio.wait_for(self._drained.wait(), timeout=5.0)
                except TimeoutError:
                    logger.warning(
                        "session_provider: drain timed out with %d in-flight",
                        self._in_flight,
                    )

        if self._session_ctx is not None:
            await self._session_ctx.__aexit__(None, None, None)
            self._session_ctx = None

        if self._read_ctx is not None:
            await self._read_ctx.__aexit__(None, None, None)
            self._read_ctx = None

        self._session = None
        logger.info("session_provider: MCP subprocess shut down")

    async def __aenter__(self) -> SessionProvider:
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute an MCP tool call against the managed session.

        If the underlying subprocess has died, transparently reconnects
        before retrying once.

        Args:
            name: MCP tool name (e.g. "aggregate", "insertOne", "updateMany", "find").
            arguments: Tool arguments dict.

        Returns:
            Raw CallToolResult from the MCP server.

        Raises:
            RuntimeError: If the session cannot be started or reconnected, or if
                the provider is shutting down.
        """
        if self._shutting_down.is_set():
            raise RuntimeError("MCP session is shutting down")

        session = self._session
        if session is None:
            raise RuntimeError("MCP session not started — has start() been called?")

        async with self._lock:
            self._in_flight += 1

        logger.debug(
            "session_provider: calling tool | tool=%s arg_keys=%s",
            name,
            list(arguments.keys()),
        )

        try:
            for attempt in range(2):
                try:
                    return await session.call_tool(name, arguments)
                except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                    if attempt == 0:
                        logger.warning(
                            "session_provider: tool call failed (attempt 1/2) | "
                            "tool=%s error=%s",
                            name,
                            exc,
                        )
                        session = await self._reconnect()
                    else:
                        raise RuntimeError(
                            f"MCP tool call '{name}' failed after reconnect: {exc}"
                        ) from exc
        finally:
            async with self._lock:
                self._in_flight -= 1
                if self._in_flight == 0:
                    self._drained.set()

    async def _reconnect(self) -> ClientSession:
        """Tear down the existing session/transport and start a fresh one."""
        logger.warning("session_provider: session lost, reconnecting")

        if self._shutting_down.is_set():
            raise RuntimeError("MCP session is shutting down")

        if self._session_ctx is not None:
            with contextlib.suppress(Exception):
                await self._session_ctx.__aexit__(None, None, None)
            self._session_ctx = None

        if self._read_ctx is not None:
            with contextlib.suppress(Exception):
                await self._read_ctx.__aexit__(None, None, None)
            self._read_ctx = None

        self._session = None

        params = get_mcp_params()
        self._read_ctx = stdio_client(params)
        read, write = await self._read_ctx.__aenter__()
        self._session_ctx = ClientSession(read, write)
        session = await self._session_ctx.__aenter__()
        await session.initialize()
        self._session = session
        logger.info("session_provider: session reconnected")
        return session


# --- Module-level singleton for application lifespan ---

_provider: SessionProvider | None = None


async def startup() -> None:
    """Start the persistent MCP subprocess via the module singleton."""
    global _provider
    logger.info("session_provider: starting write-capable MCP subprocess")
    _provider = SessionProvider()
    await _provider.start()


async def shutdown() -> None:
    """Close the persistent session and terminate subprocess."""
    global _provider
    if _provider is not None:
        await _provider.stop()
        _provider = None


async def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Execute an MCP tool call against the module singleton."""
    if _provider is None:
        raise RuntimeError("MCP session not started — has startup() been called?")
    return await _provider.call_tool(name, arguments)
