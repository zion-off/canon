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

from src.mcp.constants import (
    AgentName,
    SessionState,
    TempState,
    ToolCallStatus,
    ToolName,
)
from src.models.schemas import (
    ReasoningCheckpointEvent,
    ReasoningCheckpointPayload,
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
    if "error" in result_dict or result_dict.get("status") == ToolCallStatus.ERROR:
        return ToolCallStatus.ERROR
    return ToolCallStatus.OK


async def emit_tool_started(
    event_feed: AgentEventFeed,
    tool: BaseTool,
    tool_args: dict[str, Any],
    tool_context: ToolContext,
) -> None:
    """Generate an invocation ID, stash it in state, and broadcast tool_call_started.

    Called by ReasoningFeedPlugin for the orchestrator and directly by subagent
    before_tool_callbacks (since AgentTool sub-runners bypass App-level plugins).
    """
    invocation_id = uuid4().hex
    tool_context.state[TempState.TOOL_INV_ID.format(tool_name=tool.name)] = (
        invocation_id
    )
    agent_invocation_id: str | None = tool_context.state.get(
        TempState.AGENT_INV_ID.format(agent_name=tool_context.agent_name)
    )

    logging.getLogger(__name__).debug(
        "reasoning_feed: tool started | agent=%s tool=%s inv=%s agent_inv=%s",
        tool_context.agent_name,
        tool.name,
        invocation_id,
        agent_invocation_id,
    )
    await event_feed.broadcast(
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
                agent_invocation_id=agent_invocation_id,
            ),
        ),
    )


async def emit_tool_completed(
    event_feed: AgentEventFeed,
    tool: BaseTool,
    tool_args: dict[str, Any],
    tool_context: ToolContext,
    result: Any,
) -> None:
    """Broadcast tool_call_completed, correlating via the invocation ID in state.

    Called by ReasoningFeedPlugin for the orchestrator and directly by subagent
    after_tool_callbacks.
    """
    invocation_id = tool_context.state.get(
        TempState.TOOL_INV_ID.format(tool_name=tool.name), ""
    )
    agent_invocation_id: str | None = tool_context.state.get(
        TempState.AGENT_INV_ID.format(agent_name=tool_context.agent_name)
    )
    status = _extract_status(result)

    logging.getLogger(__name__).debug(
        "reasoning_feed: tool completed | agent=%s tool=%s inv=%s agent_inv=%s status=%s",
        tool_context.agent_name,
        tool.name,
        invocation_id,
        agent_invocation_id,
        status,
    )
    await event_feed.broadcast(
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
                agent_invocation_id=agent_invocation_id,
            ),
        ),
    )


class ReasoningFeedPlugin(BasePlugin):
    """Intercepts agent lifecycle events and emits them to the Reasoning Feed.

    Registered as an App plugin — fires for the orchestrator and all subagents.
    Captures tool invocations and agent delegations across the full hierarchy.
    Sequence numbers are assigned by AgentEventFeed.broadcast (not here).
    """

    def __init__(self, event_feed: AgentEventFeed) -> None:
        super().__init__(name="reasoning_feed")
        self._event_feed = event_feed

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        """Assign each agent invocation a unique ID and emit subagent_invoked for non-orchestrators."""
        agent_invocation_id = uuid4().hex
        callback_context.state[TempState.AGENT_INV_ID.format(agent_name=agent.name)] = (
            agent_invocation_id
        )

        if agent.name == AgentName.ORCHESTRATOR:
            return None

        logging.getLogger(__name__).info(
            "reasoning_feed: subagent invoked | agent=%s session=%s inv=%s",
            agent.name,
            callback_context.state.get(SessionState.SESSION_ID),
            agent_invocation_id,
        )
        await self._event_feed.broadcast(
            tenant_id=callback_context.state.get(SessionState.TENANT_ID),
            user_id=callback_context.state.get(SessionState.USER_ID),
            session_id=callback_context.state.get(SessionState.SESSION_ID),
            run_id=callback_context.state.get(SessionState.RUN_ID),
            event=SubagentInvokedEvent(
                author=agent.name,
                payload=SubagentInvokedPayload(
                    agent_name=agent.name,
                    agent_invocation_id=agent_invocation_id,
                ),
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
        """Emit tool_call_started, or reasoning_checkpoint for emit_checkpoint calls."""
        if tool.name == ToolName.EMIT_CHECKPOINT:
            message = tool_args.get("message", "") if tool_args else ""
            logging.getLogger(__name__).info(
                "reasoning_feed: checkpoint | agent=%s msg=%.120s",
                tool_context.agent_name,
                message,
            )
            await self._event_feed.broadcast(
                tenant_id=tool_context.state.get(SessionState.TENANT_ID),
                user_id=tool_context.state.get(SessionState.USER_ID),
                session_id=tool_context.state.get(SessionState.SESSION_ID),
                run_id=tool_context.state.get(SessionState.RUN_ID),
                event=ReasoningCheckpointEvent(
                    author=tool_context.agent_name,
                    payload=ReasoningCheckpointPayload(message=message),
                ),
            )
            return None
        await emit_tool_started(self._event_feed, tool, tool_args, tool_context)
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: Any,
    ) -> dict | None:
        """Emit tool_call_completed; skip emit_checkpoint (handled in before_tool_callback)."""
        if tool.name == ToolName.EMIT_CHECKPOINT:
            return None
        await emit_tool_completed(
            self._event_feed, tool, tool_args, tool_context, result
        )
        return None
