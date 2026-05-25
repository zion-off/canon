"""ADK plugin for the Canon Reasoning Feed.

Intercepts agent and tool lifecycle events and broadcasts them
to connected clients via the AgentEventFeed service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.genai import types

from src.mcp.constants import AgentName, EventType, SessionState
from src.mcp.utils import summarize_args, summarize_result
from src.models.schemas import AgentEvent

if TYPE_CHECKING:
    from google.adk.tools.tool_context import ToolContext

    from src.services.event_feed import AgentEventFeed


class ReasoningFeedPlugin(BasePlugin):
    """Intercepts agent lifecycle events and emits them to the Reasoning Feed.

    Registered as an App plugin — runs BEFORE any agent-level callbacks.
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
        if agent.name == AgentName.ORCHESTRATOR:
            return None

        await self._event_feed.broadcast(
            tenant_id=callback_context.state.get(SessionState.TENANT_ID),
            user_id=callback_context.state.get(SessionState.USER_ID),
            session_id=callback_context.state.get(SessionState.SESSION_ID),
            run_id=callback_context.state.get(SessionState.RUN_ID),
            event=AgentEvent(
                type=EventType.SUBAGENT_INVOKED,
                author=agent.name,
                content=f"{agent.name} started",
            ),
        )
        return None

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict | None:
        """Emit tool_call_started."""
        await self._event_feed.broadcast(
            tenant_id=tool_context.state.get(SessionState.TENANT_ID),
            user_id=tool_context.state.get(SessionState.USER_ID),
            session_id=tool_context.state.get(SessionState.SESSION_ID),
            run_id=tool_context.state.get(SessionState.RUN_ID),
            event=AgentEvent(
                type=EventType.TOOL_CALL_STARTED,
                author=tool_context.agent_name,
                content=f"{tool.name}: {summarize_args(tool_args)}",
            ),
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
        """Emit tool_call_completed with a summary of the invocation."""
        summary = summarize_result(tool.name, tool_args, result)
        await self._event_feed.broadcast(
            tenant_id=tool_context.state.get(SessionState.TENANT_ID),
            user_id=tool_context.state.get(SessionState.USER_ID),
            session_id=tool_context.state.get(SessionState.SESSION_ID),
            run_id=tool_context.state.get(SessionState.RUN_ID),
            event=AgentEvent(
                type=EventType.TOOL_CALL_COMPLETED,
                author=tool_context.agent_name,
                content=summary,
            ),
        )
        return None
