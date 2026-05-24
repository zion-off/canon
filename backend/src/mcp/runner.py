from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bson import ObjectId
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from src.config import settings
from src.mcp.agents import build_orchestrator
from src.mcp.plugin import ReasoningFeedPlugin
from src.mcp.utils import get_genai_client
from src.models.schemas import AgentEvent

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from src.services.event_feed import AgentEventFeed


async def run_agent(
    tenant_id: str,
    user_id: str,
    session_id: str,
    run_id: str,
    message: str,
    event_feed: AgentEventFeed,
    db: AsyncIOMotorDatabase,
) -> str:
    """Invoke the ADK orchestrator agent for a single request lifecycle.

    Constructs a fresh orchestrator per invocation. The session_id provides
    workflow continuity (the ADK agent can reference prior context), but no
    server-side session state persists between HTTP requests.
    """
    tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
    if not tenant:
        return "Error: tenant not found."

    # Upsert session document
    session_doc = await db.sessions.find_one_and_update(
        {"sessionId": session_id},
        {
            "$setOnInsert": {
                "tenantId": ObjectId(tenant_id),
                "userId": user_id,
                "sessionId": session_id,
                "status": "active",
                "title": message[:100],
                "summary": None,
                "createdAt": datetime.now(UTC),
            },
            "$inc": {"runCount": 1},
            "$set": {
                "updatedAt": datetime.now(UTC),
                "lastRunAt": datetime.now(UTC),
            },
        },
        upsert=True,
        return_document=True,
    )

    session_summary = session_doc.get("summary")

    orchestrator = build_orchestrator()

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="canon",
        user_id=tenant_id,
        state={
            "app:tenant_id": tenant_id,
            "app:user_id": user_id,
            "app:org_name": tenant["name"],
            "app:session_id": session_id,
            "app:run_id": run_id,
            "app:max_graph_depth": tenant.get("settings", {}).get("maxGraphDepth", 2),
            "app:embedding_model": tenant.get("embeddingModel", settings.embedding_model),
        },
    )

    canon_app = App(
        name="canon",
        root_agent=orchestrator,
        plugins=[ReasoningFeedPlugin(event_feed)],
        context_cache_config=ContextCacheConfig(
            min_tokens=2048,
            ttl_seconds=1800,
        ),
    )

    runner = Runner(
        app=canon_app,
        session_service=session_service,
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
        event=AgentEvent(
            type="run_started",
            author="canon_orchestrator",
            content=None,
            is_final=False,
        ),
    )

    # Run orchestrator — the ReasoningFeedPlugin handles lifecycle events
    # (tool_call_started, tool_call_completed, subagent_invoked) automatically.
    # This loop only detects reasoning checkpoints and the final response.
    final_response = None
    async for event in runner.run_async(
        user_id=tenant_id,
        session_id=session.id,
        new_message=content,
    ):
        function_calls: list = getattr(event, "function_calls", None) or []
        for fc in function_calls:
            if fc.name == "emit_checkpoint":
                await event_feed.broadcast(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    run_id=run_id,
                    event=AgentEvent(
                        type="reasoning_checkpoint",
                        author="canon_orchestrator",
                        content=fc.args.get("message", ""),
                        is_final=False,
                    ),
                )

        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    # Emit the final response
    if final_response:
        await event_feed.broadcast(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            event=AgentEvent(
                type="final_response",
                author="canon_orchestrator",
                content=final_response,
                is_final=True,
            ),
        )

    # Emit run_completed
    await event_feed.broadcast(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        run_id=run_id,
        event=AgentEvent(
            type="run_completed",
            author="canon_orchestrator",
            content=None,
            is_final=False,
        ),
    )

    # Update session summary for continuity
    if final_response:
        updated_summary = await _generate_session_summary(
            previous_summary=session_summary,
            request=message,
            response=final_response,
        )
        await db.sessions.update_one(
            {"sessionId": session_id},
            {"$set": {"summary": updated_summary}},
        )

    event_feed.cleanup_run(run_id)

    return final_response or "No response generated."


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

    client = get_genai_client()
    result = await client.aio.models.generate_content(
        model=f"models/{settings.fast_model}",
        contents=prompt,
    )
    if not result.text:
        return ""
    return result.text.strip()
