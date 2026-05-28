"""Low-level MCP subprocess transport and ClientSession lifecycle.

McpSession owns the stdio transport (via stdio_client) and the
ClientSession. It provides start/stop/__aenter__/__aexit__ for
lifecycle management and a plain call_tool forwarder.

SessionProvider (in provider.py) layers draining, reconnect
retry, and shutdown coordination on top.
"""

import contextlib
import logging
from typing import Any

from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp import ClientSession

logger = logging.getLogger(__name__)


class McpSession:
    """Manages stdio subprocess transport + MCP ClientSession lifecycle.

    Usage::

        async with McpSession(params) as mcp:
            result = await mcp.call_tool("find", {"filter": {}})
    """

    def __init__(self, params: StdioServerParameters) -> None:
        self._params = params
        self._read_ctx: Any = None
        self._session_ctx: Any = None
        self._session: ClientSession | None = None

    async def start(self) -> None:
        """Start the subprocess and initialize the MCP session."""
        self._read_ctx = stdio_client(self._params)
        read, write = await self._read_ctx.__aenter__()
        self._session_ctx = ClientSession(read, write)
        session = await self._session_ctx.__aenter__()
        await session.initialize()
        self._session = session
        logger.info("mcp.session: session initialized")

    async def stop(self) -> None:
        """Tear down ClientSession then stdio transport."""
        logger.info("mcp.session: shutting down")

        if self._session_ctx is not None:
            with contextlib.suppress(Exception):
                await self._session_ctx.__aexit__(None, None, None)
            self._session_ctx = None

        if self._read_ctx is not None:
            with contextlib.suppress(Exception):
                await self._read_ctx.__aexit__(None, None, None)
            self._read_ctx = None

        self._session = None

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Forward a tool call to the underlying ClientSession."""
        if self._session is None:
            raise RuntimeError("MCP session not started")
        return await self._session.call_tool(name, arguments)

    async def __aenter__(self) -> McpSession:
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()
