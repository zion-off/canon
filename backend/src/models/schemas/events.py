from __future__ import annotations

from typing import Literal

from pydantic import Field

from src.models.schemas._base import MongoModel

AgentEventType = Literal[
    "reasoning_checkpoint",
    "tool_call_started",
    "tool_call_completed",
    "subagent_invoked",
    "run_started",
    "run_completed",
    "final_response",
]


class AgentEvent(MongoModel):
    type: AgentEventType
    author: str | None = None
    content: str | None = None
    sequence: int | None = None
    timestamp: str | None = None
    is_final: bool = Field(
        default=False, validation_alias="isFinal", serialization_alias="isFinal"
    )
