"""Tenant authentication middleware for FastMCP.

Resolves the Bearer token from incoming requests, validates it against the
api_tokens collection, and stashes the resolved tenant context on the MCP
session so tools, resources, and prompts can retrieve it without repeating
the lookup.
"""

from __future__ import annotations

import logging
from typing import Any

import mcp.types as mt
from fastmcp.exceptions import AuthorizationError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

from src.services.tenant_resolver import TenantResolver

TENANT_STATE_KEY = "_canon_tenant"
USER_STATE_KEY = "_canon_user"

log = logging.getLogger(__name__)


class AuthMiddleware(Middleware):
    async def on_request(
        self,
        context: MiddlewareContext[mt.Request[Any, Any]],
        call_next: CallNext[mt.Request[Any, Any], Any],
    ) -> Any:
        request = get_http_request()
        if request is None:
            return await call_next(context)

        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
        if not token:
            raise AuthorizationError("Missing API token")

        resolver = TenantResolver()
        tenant_ctx = await resolver.resolve(token)
        if not tenant_ctx:
            log.warning("AuthMiddleware: invalid API token")
            raise AuthorizationError("Invalid API token")

        fastmcp_ctx = context.fastmcp_context
        if fastmcp_ctx is not None:
            await fastmcp_ctx.set_state(TENANT_STATE_KEY, tenant_ctx.tenant_id)
            await fastmcp_ctx.set_state(USER_STATE_KEY, tenant_ctx.user_id)

        log.info(
            "AuthMiddleware: resolved | tenant=%s user=%s",
            tenant_ctx.tenant_id,
            tenant_ctx.user_id,
        )
        return await call_next(context)
