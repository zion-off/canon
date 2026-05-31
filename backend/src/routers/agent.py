"""Agent invocation routes for MCP proxy consumption.

Auth: Bearer API token (resolved via TenantContext).
"""

from __future__ import annotations

import asyncio
import logging
from asyncio import Queue
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.agent.runner import run_agent
from src.dependencies import api_token_auth, get_event_feed
from src.models.schemas import AgentEvent
from src.models.schemas.agent import (
    AgentConfirmRequest,
    AgentConfirmResponse,
    AgentRunRequest,
)
from src.models.schemas.events import ConfirmationReceivedEvent, ConfirmationReceivedPayload
from src.services.event_feed import AgentEventFeed
from src.services.tenant_resolver import TenantContext

router = APIRouter(tags=["agent"])

log = logging.getLogger(__name__)


@router.post("/run")
async def agent_run(
    body: AgentRunRequest,
    ctx: TenantContext = Depends(api_token_auth),
    event_feed: AgentEventFeed = Depends(get_event_feed),
) -> StreamingResponse:
    """Start an agent run and stream its events as SSE.

    The response is a text/event-stream that carries all run-scoped events
    (reasoning checkpoints, tool calls, confirmation requests, final response)
    and closes naturally after run_completed. The caller does not need to know
    the run_id — filtering happens server-side.
    """
    run_id = str(uuid4())

    log.info(
        "agent_run: starting | tenant=%s session=%s run=%s",
        ctx.tenant_id,
        body.session_id,
        run_id,
    )

    # Register the queue before starting the task — guarantees no events are
    # dropped in the window between task start and the first queue.get().
    queue = event_feed.create_run_queue(ctx.tenant_id, body.session_id)

    asyncio.create_task(
        _execute_agent(
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            session_id=body.session_id,
            run_id=run_id,
            request=body.request,
            context=body.context,
            event_feed=event_feed,
        )
    )

    return StreamingResponse(
        _run_sse_stream(event_feed, ctx.tenant_id, body.session_id, run_id, queue),
        media_type="text/event-stream",
    )


@router.post("/confirm/{confirmation_id}", response_model=AgentConfirmResponse)
async def agent_confirm(
    confirmation_id: str,
    body: AgentConfirmRequest,
    event_feed: AgentEventFeed = Depends(get_event_feed),
    _ctx: TenantContext = Depends(api_token_auth),
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

    if pending.session_id:
        await event_feed.broadcast(
            tenant_id=_ctx.tenant_id,
            user_id=_ctx.user_id,
            session_id=pending.session_id,
            run_id=pending.run_id,
            event=ConfirmationReceivedEvent(
                author="agent_confirm",
                payload=ConfirmationReceivedPayload(
                    confirmation_id=confirmation_id,
                    accepted=body.accepted,
                    response=body.response,
                ),
            ),
        )

    return AgentConfirmResponse(resolved=True)


async def _run_sse_stream(
    event_feed: AgentEventFeed,
    tenant_id: str,
    session_id: str,
    run_id: str,
    queue: Queue[AgentEvent],
) -> AsyncIterator[str]:
    async for event in event_feed.iter_run(tenant_id, session_id, run_id, queue):
        yield f"data: {event.model_dump_json(by_alias=True)}\n\n"


async def _execute_agent(
    tenant_id: str,
    user_id: str,
    session_id: str,
    run_id: str,
    request: str,
    context: str,
    event_feed: AgentEventFeed,
) -> None:
    """Task that runs the agent and logs errors."""
    try:
        await run_agent(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            request=request,
            context=context,
            event_feed=event_feed,
        )
    except Exception:
        log.exception("agent_run: agent execution failed | run=%s", run_id)
