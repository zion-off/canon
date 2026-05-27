from __future__ import annotations

import logging
from uuid import UUID, uuid4

from mcp.server.fastmcp import Context

from src.agent.runner import run_agent
from src.config import settings
from src.mcp.context import build_context
from src.models.schemas import RunStartedPayload


async def canon(
    request: str,
    context: str = "",
    session_id: str | None = None,
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
        session_id: MUST be a UUID Canon returned in a previous response. NEVER
            invent, guess, or generate this value. Omit it on the first call —
            Canon will return one. On subsequent calls within the same session,
            pass back exactly the session_id Canon gave you.
        ctx: FastMCP Context — injected automatically.

    Returns:
        Organizational guidance with a session_id for multi-turn continuity.
        Always capture the session_id from the response and pass it back on
        the next call. Do not modify it.
    """
    if ctx is None:
        raise RuntimeError("Context required — FastMCP should inject it automatically.")
    log = logging.getLogger(__name__)
    request_ctx = await build_context(ctx)
    run_id = str(uuid4())

    if session_id is not None:
        try:
            UUID(session_id)
        except ValueError:
            return (
                "ERROR: The session_id you provided is not a valid UUID. "
                "Canon only accepts session IDs it originally generated. "
                "Omit session_id to start a new session, or pass back exactly "
                "the session_id value from a previous Canon response."
            )

    resolved_session_id = session_id or str(uuid4())

    log.info(
        "canon tool: invoked | tenant=%s session=%s run=%s new_session=%s request=%.120s",
        request_ctx.tenant_id,
        resolved_session_id,
        run_id,
        session_id is None,
        request,
    )

    title = await _generate_title(request)
    log.debug("canon tool: generated title | run=%s title=%s", run_id, title)

    response = await run_agent(
        tenant_id=request_ctx.tenant_id,
        user_id=request_ctx.user_id,
        session_id=resolved_session_id,
        resolved_from_closed=session_id is not None,
        run_id=run_id,
        title=title,
        message=f"Request:\n{request}\n\nContext:\n{context}",
        event_feed=request_ctx.event_feed,
        invocation_args=RunStartedPayload(request=request, context=context),
    )

    return (
        f"{response}\n\n---\nsession_id: {resolved_session_id}\n"
        f"(Save this session_id and pass it back on your next canon call "
        f"to continue this session.)"
    )


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
