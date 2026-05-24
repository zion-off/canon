from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.event_feed import AgentEventFeed


class ReasoningFeedPlugin:
    """Intercepts agent lifecycle events and emits them to the Reasoning Feed.

    Registered on the App — runs BEFORE any agent-level callbacks.
    Captures: tool invocations, agent delegations.
    Sequence numbers are assigned by AgentEventFeed.broadcast (not here).
    """

    def __init__(self, event_feed: AgentEventFeed):
        self._event_feed = event_feed

    async def before_agent_callback(self, *, callback_context: Any, **kwargs: Any) -> None:
        """Emit subagent_invoked for non-orchestrator agents."""
        tenant_id = callback_context.state.get("app:tenant_id")
        session_id = callback_context.state.get("app:session_id")
        run_id = callback_context.state.get("app:run_id")
        agent_name = callback_context.agent_name

        if agent_name != "canon_orchestrator":
            await self._event_feed.broadcast(
                tenant_id=tenant_id,
                session_id=session_id,
                run_id=run_id,
                event={
                    "type": "subagent_invoked",
                    "author": agent_name,
                    "content": f"{agent_name} started",
                    "isFinal": False,
                },
            )
        return None

    async def before_tool_callback(
        self, *, callback_context: Any, tool_name: str, args: dict, **kwargs: Any
    ) -> dict | None:
        """Emit tool_call_started."""
        tenant_id = callback_context.state.get("app:tenant_id")
        session_id = callback_context.state.get("app:session_id")
        run_id = callback_context.state.get("app:run_id")

        await self._event_feed.broadcast(
            tenant_id=tenant_id,
            session_id=session_id,
            run_id=run_id,
            event={
                "type": "tool_call_started",
                "author": callback_context.agent_name,
                "content": f"{tool_name}: {_summarize_args(args)}",
                "isFinal": False,
            },
        )
        return None

    async def after_tool_callback(
        self, *, callback_context: Any, tool_name: str, result: Any, **kwargs: Any
    ) -> dict | None:
        """Emit tool_call_completed."""
        tenant_id = callback_context.state.get("app:tenant_id")
        session_id = callback_context.state.get("app:session_id")
        run_id = callback_context.state.get("app:run_id")

        await self._event_feed.broadcast(
            tenant_id=tenant_id,
            session_id=session_id,
            run_id=run_id,
            event={
                "type": "tool_call_completed",
                "author": callback_context.agent_name,
                "content": f"{tool_name} completed",
                "isFinal": False,
            },
        )
        return None


def _summarize_args(args: dict) -> str:
    """Produce a human-readable summary of tool arguments for the feed."""
    if "query" in args:
        return str(args["query"])[:100]
    if "document" in args and isinstance(args["document"], dict) and "name" in args["document"]:
        return f"writing: {args['document']['name']}"
    return ", ".join(f"{k}={str(v)[:50]}" for k, v in list(args.items())[:3])
