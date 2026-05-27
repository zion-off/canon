from __future__ import annotations

import logging
from uuid import uuid4

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.agent.runner import run_agent
from src.config import settings
from src.mcp.context import build_context
from src.mcp.server import mcp
from src.models.schemas import RunStartedPayload


@mcp.tool(
    name="canon",
    annotations=ToolAnnotations(
        title="check organizational memory",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def canon(
    request: str,
    context: str = "",
    ctx: Context | None = None,
) -> str:
    """Check organizational memory before planning or implementing code changes.

    Call this BEFORE writing or modifying any code. It queries your team's
    organizational knowledge graph for deprecated patterns, active migrations,
    architecture decisions, prior failures, and relevant context — and returns
    actionable guidance that should reshape your implementation plan.

    Args:
        request: Natural-language summary of what you intend to implement and why.
        context: What you have observed about the codebase — technology choices,
            existing patterns, relevant libraries, architectural decisions visible
            in the code.
        ctx: FastMCP Context — injected automatically.

    Returns:
        Organizational guidance. Sessions are tracked automatically by the MCP
        transport — no session_id argument needed.
    """
    if ctx is None:
        raise RuntimeError("Context required — FastMCP should inject it automatically.")
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
