"""Request context middleware for FastMCP.

Reads tenant context stashed by AuthMiddleware and builds a RequestContext,
making it available to all downstream tools, resources, and prompts via
get_request_context().
"""

from __future__ import annotations

import logging
from typing import Any

import mcp.types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

from src.constants import SessionState
from src.mcp.request_context import RequestContext, set_request_context
from src.services.event_feed import get_feed

log = logging.getLogger(__name__)


class ContextMiddleware(Middleware):
    async def on_request(
        self,
        context: MiddlewareContext[mt.Request[Any, Any]],
        call_next: CallNext[mt.Request[Any, Any], Any],
    ) -> Any:
        fastmcp_ctx = context.fastmcp_context
        if fastmcp_ctx is None:
            return await call_next(context)

        tenant_id = await fastmcp_ctx.get_state(SessionState.TENANT)
        user_id = await fastmcp_ctx.get_state(SessionState.USER)

        if not tenant_id or not user_id:
            raise ValueError("Not authenticated — AuthMiddleware must run first")

        log.debug(
            "ContextMiddleware: building request context | tenant=%s user=%s",
            tenant_id,
            user_id,
        )

        set_request_context(
            RequestContext(
                tenant_id=tenant_id,
                user_id=user_id,
                event_feed=get_feed(),
                fastmcp_ctx=fastmcp_ctx,
            )
        )

        return await call_next(context)
