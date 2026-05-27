"""Emit checkpoint tool — records reasoning milestones for the Reasoning Feed."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.agent.constants import TempState


async def emit_checkpoint(message: str, tool_context: ToolContext) -> dict[str, str]:
    """Emit a reasoning checkpoint visible to the user."""
    checkpoints: list[dict[str, Any]] = tool_context.state.get(
        TempState.CHECKPOINTS, []
    )
    checkpoints.append({"message": message, "timestamp": datetime.now(UTC).isoformat()})
    tool_context.state[TempState.CHECKPOINTS] = checkpoints
    logging.getLogger(__name__).info(
        "emit_checkpoint: agent=%s msg=%.120s",
        tool_context.agent_name,
        message,
    )
    return {"status": "ok", "message": message}


emit_checkpoint_tool = FunctionTool(func=emit_checkpoint)
