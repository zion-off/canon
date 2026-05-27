"""Agent run loop — constructs the ADK runner and executes agent invocations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bson import ObjectId
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from src.agent.agent_platform import CanonModel
from src.agent.agents.orchestrator import build_orchestrator
from src.agent.constants import (
    AgentName,
    SessionState,
)
from src.agent.plugins.ambient_context import AmbientContextPlugin
from src.agent.plugins.reasoning_feed import ReasoningFeedPlugin
from src.config import settings
from src.models.documents import SessionDocument, TenantDocument
from src.models.schemas import (
    FinalResponseEvent,
    FinalResponsePayload,
    RunCompletedEvent,
    RunStartedEvent,
    RunStartedPayload,
    SessionResponse,
)

if TYPE_CHECKING:
    from src.services.event_feed import AgentEventFeed


async def run_agent(
    tenant_id: str,
    user_id: str,
    session_id: str,
    run_id: str,
    title: str,
    message: str,
    event_feed: AgentEventFeed,
    invocation_args: RunStartedPayload | None = None,
) -> str:
    """Invoke the ADK orchestrator agent for a single request lifecycle.

    Constructs a fresh orchestrator per invocation. The session_id provides
    workflow continuity (the ADK agent can reference prior context), but no
    server-side session state persists between HTTP requests.

    session_id comes from the MCP transport and is guaranteed stable within
    a client session.
    """
    log = logging.getLogger(__name__)
    log.info(
        "run_agent: starting | tenant=%s user=%s session=%s run=%s",
        tenant_id,
        user_id,
        session_id,
        run_id,
    )

    tenant_oid = ObjectId(tenant_id)
    tenant = await TenantDocument.get(tenant_oid)
    if not tenant:
        log.warning("run_agent: tenant not found | tenant=%s", tenant_id)
        return (
            "Error: your tenant account could not be found. "
            "Please verify your API token is correct and active. "
            "If the issue persists, contact your Canon administrator."
        )

    # Upsert session — find or create, then increment run count.
    now = datetime.now(UTC)
    session = await SessionDocument.find_one(SessionDocument.session_id == session_id)
    if session is None:
        session = SessionDocument.model_construct(
            session_id=session_id,
            tenant_id=tenant_oid,
            user_id=user_id,
            title=title,
            summary=None,
            run_count=1,
            created_at=now,
            updated_at=now,
            last_run_at=now,
        )
        await session.insert()
        log.info(
            "run_agent: created session | session=%s title=%s",
            session_id,
            title,
        )
    else:
        session.run_count += 1
        session.updated_at = now
        session.last_run_at = now
        await session.save()
        log.info(
            "run_agent: reusing session | session=%s run_count=%d",
            session_id,
            session.run_count,
        )

    session_summary = session.summary

    # Notify live subscribers that a session was created or updated
    await event_feed.broadcast_session(
        tenant_id,
        SessionResponse.model_validate(session.model_dump(by_alias=True)),
    )

    log.debug("run_agent: building orchestrator | run=%s", run_id)
    orchestrator = build_orchestrator()

    log.debug("run_agent: creating ADK session | run=%s", run_id)
    session_service = InMemorySessionService()
    adk_session = await session_service.create_session(
        app_name="canon",
        user_id=tenant_id,
        state={
            SessionState.TENANT_ID: tenant_id,
            SessionState.USER_ID: user_id,
            SessionState.ORG_NAME: tenant.name,
            SessionState.SESSION_ID: session_id,
            SessionState.RUN_ID: run_id,
            SessionState.MAX_GRAPH_DEPTH: tenant.settings.get("maxGraphDepth", 2),
            SessionState.EMBEDDING_MODEL: tenant.embedding_model,
        },
    )
    log.debug(
        "run_agent: ADK session created | run=%s adk_session_id=%s",
        run_id,
        adk_session.id,
    )

    canon_app = App(
        name="canon",
        root_agent=orchestrator,
        plugins=[AmbientContextPlugin(), ReasoningFeedPlugin(event_feed)],
        context_cache_config=ContextCacheConfig(
            min_tokens=2048,
            ttl_seconds=1800,
        ),
    )

    runner = Runner(
        app=canon_app,
        session_service=session_service,
    )
    log.debug(
        "run_agent: ADK runner ready | run=%s reasoning_model=%s",
        run_id,
        settings.reasoning_model,
    )

    content = Content(
        role="user",
        parts=[Part.from_text(text=_build_message(message, session_summary))],
    )

    # Emit run_started
    await event_feed.broadcast(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        run_id=run_id,
        event=RunStartedEvent(
            author=AgentName.ORCHESTRATOR,
            payload=invocation_args or RunStartedPayload(request="", context=""),
        ),
    )

    # Run orchestrator — ReasoningFeedPlugin handles all lifecycle events including
    # checkpoints. This loop only captures the final response text.
    log.info(
        "run_agent: starting ADK run loop | run=%s model=%s",
        run_id,
        settings.reasoning_model,
    )
    final_response = None
    event_count = 0
    async for event in runner.run_async(
        user_id=tenant_id,
        session_id=adk_session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
        event_count += 1

    log.info(
        "run_agent: ADK run loop finished | run=%s event_count=%d has_response=%s",
        run_id,
        event_count,
        bool(final_response),
    )

    # Emit the final response
    if final_response:
        await event_feed.broadcast(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            event=FinalResponseEvent(
                author=AgentName.ORCHESTRATOR,
                is_final=True,
                payload=FinalResponsePayload(text=final_response),
            ),
        )
        log.info(
            "run_agent: final response emitted | run=%s len=%d",
            run_id,
            len(final_response),
        )
    else:
        log.warning("run_agent: no final response | run=%s", run_id)

    # Emit run_completed
    await event_feed.broadcast(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        run_id=run_id,
        event=RunCompletedEvent(author=AgentName.ORCHESTRATOR),
    )

    # Update session summary for continuity
    if final_response:
        log.debug("run_agent: generating session summary | run=%s", run_id)
        updated_summary = await _generate_session_summary(
            previous_summary=session_summary,
            request=message,
            response=final_response,
        )
        await SessionDocument.find_one(SessionDocument.session_id == session_id).set(
            {SessionDocument.summary: updated_summary}
        )
        log.debug(
            "run_agent: session summary updated | session=%s prev_summary=%s new_summary=%s",
            session_id,
            bool(session_summary),
            bool(updated_summary),
        )

    # Notify subscribers of updated session state (summary, run_count)
    updated_session = await SessionDocument.find_one(
        SessionDocument.session_id == session_id
    )
    if updated_session:
        await event_feed.broadcast_session(
            tenant_id,
            SessionResponse.model_validate(updated_session.model_dump(by_alias=True)),
        )

    event_feed.cleanup_session(session_id)
    log.debug("run_agent: cleaned up sequence tracking | session=%s", session_id)

    log.info(
        "run_agent: complete | session=%s run=%s events=%d",
        session_id,
        run_id,
        event_count,
    )
    return final_response or (
        "No response was generated. This may indicate a temporary issue with the "
        "model or that your request was too ambiguous to process. "
        "Try rephrasing your request with more specific detail."
    )


def _build_message(request: str, session_summary: str | None) -> str:
    """Construct the message sent to the orchestrator, with session context."""
    if session_summary:
        return f"[Prior session context: {session_summary}]\n\nRequest:\n{request}"
    return f"Request:\n{request}"


async def _generate_session_summary(
    previous_summary: str | None,
    request: str,
    response: str,
) -> str:
    """Generate a rolling semantic summary of the session's evolving context.

    Uses FAST_MODEL for cost-efficiency — this is a compression task, not reasoning.
    """
    prompt = f"""\
Produce an aggressively concise semantic summary (2-3 sentences max) of this session.
Capture ONLY: key decisions made, memory nodes written, and open threads that affect the next run.
Omit pleasantries, reasoning process, and anything retrievable from the knowledge graph.

{"Previous summary: " + previous_summary if previous_summary else "This is the first run in this session."}

Latest request: {request[:500]}
Latest response: {response[:1000]}

Write only the updated summary — no preamble, no explanation. Ruthlessly compress."""

    try:
        summary = await CanonModel.generate_text(settings.fast_model, prompt)
        return summary or ""
    except Exception:
        logging.getLogger(__name__).exception("Session summary generation failed")
        return ""
