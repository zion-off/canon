"""Agent invocation routes for MCP proxy consumption.

Auth: Bearer API token (resolved via TenantContext).
"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.agent.runner import run_agent
from src.dependencies import api_token_auth, get_event_feed
from src.models.schemas.agent import (
    AgentConfirmRequest,
    AgentConfirmResponse,
    AgentRunRequest,
    AgentRunResponse,
)
from src.services.event_feed import AgentEventFeed
from src.services.tenant_resolver import TenantContext

router = APIRouter(tags=["agent"])

log = logging.getLogger(__name__)


@router.post("/run", response_model=AgentRunResponse)
async def agent_run(
    body: AgentRunRequest,
    background_tasks: BackgroundTasks,
    ctx: TenantContext = Depends(api_token_auth),
    event_feed: AgentEventFeed = Depends(get_event_feed),
) -> AgentRunResponse:
    """Start an agent run for the given session.

    The caller should immediately subscribe to the SSE stream at
    ``GET /api/v1/sessions/{session_id}/stream`` to receive events
    including checkpoints, confirmation requests, and the final response.
    """
    run_id = str(uuid4())

    log.info(
        "agent_run: starting | tenant=%s session=%s run=%s",
        ctx.tenant_id,
        body.session_id,
        run_id,
    )

    background_tasks.add_task(
        _execute_agent,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        session_id=body.session_id,
        run_id=run_id,
        title=body.title or body.request[:80],
        request=body.request,
        context=body.context,
        event_feed=event_feed,
    )

    return AgentRunResponse(
        runId=run_id, sessionId=body.session_id, tenantId=ctx.tenant_id
    )


@router.post("/confirm/{confirmation_id}", response_model=AgentConfirmResponse)
async def agent_confirm(
    confirmation_id: str,
    body: AgentConfirmRequest,
    event_feed: AgentEventFeed = Depends(get_event_feed),
) -> AgentConfirmResponse:
    """Resolve a pending confirmation request.

    Called by the MCP proxy after the user responds to an elicit prompt.
    The confirmation_id is the run-scoped ID that was broadcast in the
    ``confirmation_requested`` event.
    """
    pending = await event_feed.resolve_confirmation(
        confirmation_id=confirmation_id,
        accepted=body.accepted,
        response=body.response,
    )
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="Confirmation not found or already resolved",
        )
    return AgentConfirmResponse(resolved=True)


async def _execute_agent(
    tenant_id: str,
    user_id: str,
    session_id: str,
    run_id: str,
    title: str,
    request: str,
    context: str,
    event_feed: AgentEventFeed,
) -> None:
    """Background task that runs the agent and handles errors."""
    try:
        await run_agent(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            title=title,
            request=request,
            context=context,
            event_feed=event_feed,
        )
    except Exception:
        log.exception("agent_run: agent execution failed | run=%s", run_id)
