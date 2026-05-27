from __future__ import annotations

import logging
from typing import Annotated
from uuid import uuid4

from fastmcp import Context
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from src.agent.runner import run_agent
from src.config import settings
from src.mcp.context import build_context, set_mcp_context
from src.models.schemas import RunStartedPayload


@tool(
    name="canon",
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
    ctx: Context,  # auto-excluded from MCP input schema by FastMCP
    request: Annotated[
        str,
        Field(description="Natural-language summary of what you intend to implement and why."),
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
) -> str:
    """Check organizational memory before planning or implementing code changes.

    Call this BEFORE writing or modifying any code. It queries your team's
    organizational knowledge graph for deprecated patterns, active migrations,
    architecture decisions, prior failures, and relevant context — and returns
    actionable guidance that should reshape your implementation plan.
    """
    set_mcp_context(ctx)
    log = logging.getLogger(__name__)
    request_ctx = await build_context(ctx)
    run_id = str(uuid4())

    session_id = ctx.session_id

    log.info(
        "canon tool: invoked | tenant=%s session=%s run=%s request=%.120s",
        request_ctx.tenant_id,
        session_id,
        run_id,
        request,
    )

    title = await _generate_title(request)
    log.debug("canon tool: generated title | run=%s title=%s", run_id, title)

    response = await run_agent(
        tenant_id=request_ctx.tenant_id,
        user_id=request_ctx.user_id,
        session_id=session_id,
        run_id=run_id,
        title=title,
        message=f"Request:\n{request}\n\nContext:\n{context}",
        event_feed=request_ctx.event_feed,
        invocation_args=RunStartedPayload(request=request, context=context),
    )

    return response


async def _generate_title(request: str) -> str:
    """Generate a 5-6 word title from the raw request. Falls back to truncation."""
    from src.agent.agent_platform import CanonModel

    prompt = f"""\
Generate a concise title (5-6 words max) for a coding session based on this request.
Return ONLY the title — no quotes, no preamble, no explanation.

Request: {request[:500]}

Title:"""

    try:
        title = await CanonModel.generate_text(settings.fast_model, prompt)
        if title:
            return title.strip()
    except Exception:
        logging.getLogger(__name__).exception("Title generation failed")

    return request[:100]
