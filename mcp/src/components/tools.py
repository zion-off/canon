"""Canon tool — calls the backend agent run endpoint and streams events via SSE."""

from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastmcp import Context
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from src.config import settings
from src.constants import (
    AuthScheme,
    EventPayload,
    ToolName,
)
from src.sse import consume_sse

log = logging.getLogger(__name__)


@tool(
    name=ToolName.CANON,
    annotations=ToolAnnotations(
        title="check organizational memory",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
    description=(
        "Check organizational memory before planning or implementing code changes. "
        "Call this BEFORE writing or modifying any code. It queries your team's "
        "organizational knowledge graph for deprecated patterns, active migrations, "
        "architecture decisions, prior failures, and relevant context — and returns "
        "actionable guidance that should reshape your implementation plan."
    ),
)
async def canon(
    request: Annotated[
        str,
        Field(
            description="Natural-language summary of what you intend to implement and why."
        ),
    ],
    context: Annotated[
        str,
        Field(
            default="",
            description=(
                "What you have observed about the codebase — technology choices, "
                "existing patterns, relevant libraries, architectural decisions "
                "visible in the code."
            ),
        ),
    ] = "",
    fastmcp_ctx: Context | None = None,
) -> str:
    """Check organizational memory before implementing code changes.

    POSTs to /agent/run, which starts the agent and streams SSE events directly
    in the response. Progress and confirmation requests are handled inline;
    the connection closes naturally after run_completed.
    """
    if not fastmcp_ctx:
        return "Error: no MCP context available"

    session_id = fastmcp_ctx.session_id
    if not session_id:
        return "Error: no MCP session ID available"

    auth_header = f"{AuthScheme.BEARER} {settings.canon_api_token}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(300)) as client:
        return await consume_sse(
            client=client,
            body={
                EventPayload.SESSION_ID: session_id,
                EventPayload.REQUEST: request,
                EventPayload.CONTEXT: context,
            },
            auth_header=auth_header,
            fastmcp_ctx=fastmcp_ctx,
        )
