from __future__ import annotations

import contextvars

from fastmcp import Context

from src.services.event_feed import AgentEventFeed

_request_context: contextvars.ContextVar[RequestContext | None] = (
    contextvars.ContextVar("request_context", default=None)
)


class RequestContext:
    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        event_feed: AgentEventFeed,
        fastmcp_ctx: Context,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.event_feed = event_feed
        self.fastmcp_ctx = fastmcp_ctx


def set_request_context(ctx: RequestContext) -> None:
    _request_context.set(ctx)


def get_request_context() -> RequestContext:
    rc = _request_context.get()
    if rc is None:
        raise RuntimeError("RequestContext not set — ContextMiddleware must run first")
    return rc
