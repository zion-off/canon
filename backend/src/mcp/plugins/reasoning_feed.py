"""ADK plugin for the Canon Reasoning Feed.

Intercepts agent and tool lifecycle events and broadcasts them
to connected clients via the AgentEventFeed service.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.genai import types
from pydantic import BaseModel

from src.mcp.constants import AgentName, SessionState
from src.models.schemas import (
    SubagentInvokedEvent,
    SubagentInvokedPayload,
    ToolCallCompletedEvent,
    ToolCallCompletedPayload,
    ToolCallStartedEvent,
    ToolCallStartedPayload,
)

if TYPE_CHECKING:
    from google.adk.tools.tool_context import ToolContext

    from src.services.event_feed import AgentEventFeed

_INV_ID_STATE_KEY = "temp:tool_invocation_id:{tool_name}"


def _serialize_result(result: Any) -> Any:
    """Convert a tool result to a JSON-serializable value."""
    if isinstance(result, BaseModel):
        return result.model_dump()
    return result


def _extract_status(result: Any) -> str:
    """Extract a status string from a tool result."""
    if isinstance(result, BaseModel):
        result_dict = result.model_dump()
    elif isinstance(result, dict):
        result_dict = result
    else:
        return "ok"
    if "error" in result_dict:
        return "error"
    return str(result_dict.get("status", "ok"))


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

        logging.getLogger(__name__).info(
            "reasoning_feed: subagent invoked | agent=%s session=%s",
            agent.name,
            callback_context.state.get(SessionState.SESSION_ID),
        )
        await self._event_feed.broadcast(
            tenant_id=callback_context.state.get(SessionState.TENANT_ID),
            user_id=callback_context.state.get(SessionState.USER_ID),
            session_id=callback_context.state.get(SessionState.SESSION_ID),
            run_id=callback_context.state.get(SessionState.RUN_ID),
            event=SubagentInvokedEvent(
                author=agent.name,
                payload=SubagentInvokedPayload(agent_name=agent.name),
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
        """Emit tool_call_started and stash an invocation ID for correlation."""
        invocation_id = uuid4().hex
        tool_context.state[_INV_ID_STATE_KEY.format(tool_name=tool.name)] = (
            invocation_id
        )

        logging.getLogger(__name__).debug(
            "reasoning_feed: tool started | agent=%s tool=%s inv=%s",
            tool_context.agent_name,
            tool.name,
            invocation_id,
        )
        await self._event_feed.broadcast(
            tenant_id=tool_context.state.get(SessionState.TENANT_ID),
            user_id=tool_context.state.get(SessionState.USER_ID),
            session_id=tool_context.state.get(SessionState.SESSION_ID),
            run_id=tool_context.state.get(SessionState.RUN_ID),
            event=ToolCallStartedEvent(
                author=tool_context.agent_name,
                payload=ToolCallStartedPayload(
                    tool_name=tool.name,
                    args=tool_args,
                    invocation_id=invocation_id,
                ),
            ),
        )
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: Any,
    ) -> dict | None:
        """Emit tool_call_completed with the full structured result."""
        invocation_id = tool_context.state.get(
            _INV_ID_STATE_KEY.format(tool_name=tool.name), ""
        )
        status = _extract_status(result)

        logging.getLogger(__name__).debug(
            "reasoning_feed: tool completed | agent=%s tool=%s inv=%s status=%s",
            tool_context.agent_name,
            tool.name,
            invocation_id,
            status,
        )
        await self._event_feed.broadcast(
            tenant_id=tool_context.state.get(SessionState.TENANT_ID),
            user_id=tool_context.state.get(SessionState.USER_ID),
            session_id=tool_context.state.get(SessionState.SESSION_ID),
            run_id=tool_context.state.get(SessionState.RUN_ID),
            event=ToolCallCompletedEvent(
                author=tool_context.agent_name,
                payload=ToolCallCompletedPayload(
                    tool_name=tool.name,
                    args=tool_args,
                    result=_serialize_result(result),
                    status=status,
                    invocation_id=invocation_id,
                ),
            ),
        )
        return None
