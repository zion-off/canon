from __future__ import annotations

import contextvars
import logging

from fastmcp import Context

from src.mcp.middleware import TENANT_STATE_KEY, USER_STATE_KEY
from src.services.event_feed import AgentEventFeed, get_feed

_mcp_context: contextvars.ContextVar[Context | None] = contextvars.ContextVar(
    "mcp_context", default=None
)


def set_mcp_context(ctx: Context) -> None:
    _mcp_context.set(ctx)


def get_mcp_context() -> Context | None:
    return _mcp_context.get()


class _RequestContext:
    """Request-scoped dependency container resolved from MCP context."""

    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        event_feed: AgentEventFeed,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.event_feed = event_feed


async def build_context(ctx: Context) -> _RequestContext:
    """Read tenant context previously stashed by AuthMiddleware."""
    tenant_id = await ctx.get_state(TENANT_STATE_KEY)
    user_id = await ctx.get_state(USER_STATE_KEY)

    if not tenant_id or not user_id:
        raise ValueError("Not authenticated — AuthMiddleware must run first")

    log = logging.getLogger(__name__)
    log.debug(
        "build_context: resolved from session state | tenant=%s user=%s",
        tenant_id,
        user_id,
    )
    return _RequestContext(
        tenant_id=tenant_id,
        user_id=user_id,
        event_feed=get_feed(),
    )
