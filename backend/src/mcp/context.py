from __future__ import annotations

import logging

from mcp.server.fastmcp import Context

from src.services.event_feed import AgentEventFeed, get_feed
from src.services.tenant_resolver import TenantResolver


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
    """Extract tenant context from the MCP request's underlying HTTP transport."""
    request = ctx.request_context.request
    if request is None:
        raise ValueError("No HTTP request available in MCP context")
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    log = logging.getLogger(__name__)
    log.debug(
        "build_context: resolving tenant from token prefix=%s...",
        token[:8] if token else "(none)",
    )
    resolver = TenantResolver()
    tenant_ctx = await resolver.resolve(token)

    if not tenant_ctx:
        log.warning("build_context: invalid API token")
        raise ValueError("Invalid API token")

    log.info(
        "build_context: resolved | tenant=%s user=%s",
        tenant_ctx.tenant_id,
        tenant_ctx.user_id,
    )
    return _RequestContext(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        event_feed=get_feed(),
    )
