"""ADK plugin for the Canon Reasoning Feed.

Intercepts agent and tool lifecycle events and broadcasts them
to connected clients via the AgentEventFeed service.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.genai import types
from pydantic import BaseModel

from src.mcp.constants import AgentName, EventType, SessionState
from src.models.schemas import AgentEvent

if TYPE_CHECKING:
    from google.adk.tools.tool_context import ToolContext

    from src.services.event_feed import AgentEventFeed


def _summarize_args(args: dict[str, Any] | None) -> str:
    """Produce a human-readable summary of tool arguments for the event feed."""
    if not args:
        return ""
    if "query" in args:
        return str(args["query"])[:100]
    if (
        "document" in args
        and isinstance(args["document"], dict)
        and "name" in args["document"]
    ):
        return f"writing: {args['document']['name']}"
    return ", ".join(f"{k}={str(v)[:50]}" for k, v in list(args.items())[:3])


def _summarize_result(tool_name: str, args: dict[str, Any], result: Any) -> str:
    """Produce a concise summary of a completed tool invocation."""
    arg_hint = _summarize_args(args)
    if isinstance(result, BaseModel):
        model_dict = result.model_dump()
        if "error" in model_dict:
            status = "error"
        elif "status" in model_dict:
            status = model_dict["status"]
        else:
            status = "ok"
    elif isinstance(result, dict):
        status = result.get("status", "ok")
    else:
        status = "ok"
    return f"{tool_name}({arg_hint}) -> {status}"


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
        log = logging.getLogger(__name__)
        if agent.name == AgentName.ORCHESTRATOR:
            return None

        log.info(
            "reasoning_feed: subagent invoked | agent=%s session=%s",
            agent.name,
            callback_context.state.get(SessionState.SESSION_ID),
        )
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
        logging.getLogger(__name__).debug(
            "reasoning_feed: tool started | agent=%s tool=%s args=%s",
            tool_context.agent_name,
            tool.name,
            _summarize_args(tool_args),
        )
        await self._event_feed.broadcast(
            tenant_id=tool_context.state.get(SessionState.TENANT_ID),
            user_id=tool_context.state.get(SessionState.USER_ID),
            session_id=tool_context.state.get(SessionState.SESSION_ID),
            run_id=tool_context.state.get(SessionState.RUN_ID),
            event=AgentEvent(
                type=EventType.TOOL_CALL_STARTED,
                author=tool_context.agent_name,
                content=f"{tool.name}: {_summarize_args(tool_args)}",
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
        """Emit tool_call_completed with a summary of the invocation."""
        summary = _summarize_result(tool.name, tool_args, result)
        logging.getLogger(__name__).debug(
            "reasoning_feed: tool completed | agent=%s summary=%s",
            tool_context.agent_name,
            summary,
        )
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
