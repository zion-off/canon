from __future__ import annotations

from typing import TYPE_CHECKING, Any

from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

if TYPE_CHECKING:
    from google.adk.agents.base_agent import BaseAgent
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.events import Event
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.tool_context import ToolContext

    from src.services.event_feed import AgentEventFeed


class ReasoningFeedPlugin(BasePlugin):
    """Intercepts agent lifecycle events and emits them to the Reasoning Feed.

    Registered as a Runner plugin — runs BEFORE any agent-level callbacks.
    Captures: tool invocations, agent delegations.
    Sequence numbers are assigned by AgentEventFeed.broadcast (not here).
    """

    def __init__(self, event_feed: AgentEventFeed) -> None:
        super().__init__(name="reasoning_feed")
        self._event_feed = event_feed

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
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

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        """No-op: required by BasePlugin interface."""
        return None

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict | None:
        """Emit tool_call_started."""
        tenant_id = tool_context.state.get("app:tenant_id")
        session_id = tool_context.state.get("app:session_id")
        run_id = tool_context.state.get("app:run_id")

        await self._event_feed.broadcast(
            tenant_id=tenant_id,
            session_id=session_id,
            run_id=run_id,
            event={
                "type": "tool_call_started",
                "author": tool_context.agent_name,
                "content": f"{tool.name}: {_summarize_args(tool_args)}",
                "isFinal": False,
            },
        )
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> dict | None:
        """Emit tool_call_completed."""
        tenant_id = tool_context.state.get("app:tenant_id")
        session_id = tool_context.state.get("app:session_id")
        run_id = tool_context.state.get("app:run_id")

        await self._event_feed.broadcast(
            tenant_id=tenant_id,
            session_id=session_id,
            run_id=run_id,
            event={
                "type": "tool_call_completed",
                "author": tool_context.agent_name,
                "content": f"{tool.name} completed",
                "isFinal": False,
            },
        )
        return None

    async def before_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> types.Content | None:
        """No-op: required by BasePlugin interface."""
        return None

    async def after_run_callback(
        self, *, invocation_context: InvocationContext
    ) -> None:
        """No-op: required by BasePlugin interface."""

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ) -> Event | None:
        """No-op: required by BasePlugin interface."""
        return None


def _summarize_args(args: dict[str, Any]) -> str:
    """Produce a human-readable summary of tool arguments for the feed."""
    if "query" in args:
        return str(args["query"])[:100]
    if "document" in args and isinstance(args["document"], dict) and "name" in args["document"]:
        return f"writing: {args['document']['name']}"
    return ", ".join(f"{k}={str(v)[:50]}" for k, v in list(args.items())[:3])
