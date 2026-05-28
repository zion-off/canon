from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from src.agent.constants import EventType
from src.models.schemas._base import MongoModel

# ── Payload models ────────────────────────────────────────────────────────────


class RunStartedPayload(BaseModel):
    request: str
    context: str


class RunCompletedPayload(BaseModel):
    pass


class ReasoningCheckpointPayload(BaseModel):
    message: str


class FinalResponsePayload(BaseModel):
    text: str


class SubagentInvokedPayload(BaseModel):
    agent_name: str
    agent_invocation_id: str


class ToolCallStartedPayload(BaseModel):
    tool_name: str
    args: dict[str, Any]
    invocation_id: str
    agent_invocation_id: str | None = None


class ToolCallCompletedPayload(BaseModel):
    tool_name: str
    args: dict[str, Any]
    result: Any
    status: str
    invocation_id: str
    agent_invocation_id: str | None = None


class ConfirmationRequestedPayload(BaseModel):
    confirmation_id: str = Field(alias="confirmationId")
    message: str
    options: list[str]
    title: str | None = None
    description: str | None = None


class ConfirmationReceivedPayload(BaseModel):
    accepted: bool
    response: str | None = None


# ── Base event ────────────────────────────────────────────────────────────────


class AgentEventBase(MongoModel):
    """Envelope fields shared by every event type.

    ``type`` is intentionally absent here so subclasses can declare it as a
    ``Literal`` without triggering invariant-override errors. Every concrete
    subclass defines ``type`` and a typed ``payload``.
    Prefer ``AgentEvent`` for all annotations; use this base only for
    isinstance checks and internal helpers that don't need to access ``type``.
    """

    author: str | None = None
    sequence: int | None = None
    timestamp: str | None = None
    run_id: str | None = Field(
        default=None, validation_alias="runId", serialization_alias="runId"
    )
    is_final: bool = Field(
        default=False, validation_alias="isFinal", serialization_alias="isFinal"
    )

    @classmethod
    def from_document(cls, doc: dict[str, Any]) -> AgentEvent:
        """Reconstruct a typed event from a stored MongoDB document dict."""
        event_type = doc.get("type", "")
        subtype = _EVENT_REGISTRY.get(event_type)
        if subtype is None:
            raise ValueError(f"Unknown event type: {event_type!r}")
        return subtype.model_validate(doc)


# ── Typed event subclasses ────────────────────────────────────────────────────


class RunStartedEvent(AgentEventBase):
    type: Literal["run_started"] = EventType.RUN_STARTED
    payload: RunStartedPayload


class RunCompletedEvent(AgentEventBase):
    type: Literal["run_completed"] = EventType.RUN_COMPLETED
    payload: RunCompletedPayload = Field(default_factory=RunCompletedPayload)


class ReasoningCheckpointEvent(AgentEventBase):
    type: Literal["reasoning_checkpoint"] = EventType.REASONING_CHECKPOINT
    payload: ReasoningCheckpointPayload


class FinalResponseEvent(AgentEventBase):
    type: Literal["final_response"] = EventType.FINAL_RESPONSE
    payload: FinalResponsePayload


class SubagentInvokedEvent(AgentEventBase):
    type: Literal["subagent_invoked"] = EventType.SUBAGENT_INVOKED
    payload: SubagentInvokedPayload


class ToolCallStartedEvent(AgentEventBase):
    type: Literal["tool_call_started"] = EventType.TOOL_CALL_STARTED
    payload: ToolCallStartedPayload


class ToolCallCompletedEvent(AgentEventBase):
    type: Literal["tool_call_completed"] = EventType.TOOL_CALL_COMPLETED
    payload: ToolCallCompletedPayload


class ConfirmationRequestedEvent(AgentEventBase):
    type: Literal["confirmation_requested"] = EventType.CONFIRMATION_REQUESTED
    payload: ConfirmationRequestedPayload


class ConfirmationReceivedEvent(AgentEventBase):
    type: Literal["confirmation_received"] = EventType.CONFIRMATION_RECEIVED
    payload: ConfirmationReceivedPayload


# ── Discriminated union ───────────────────────────────────────────────────────

AgentEvent = Annotated[
    RunStartedEvent
    | RunCompletedEvent
    | ReasoningCheckpointEvent
    | FinalResponseEvent
    | SubagentInvokedEvent
    | ToolCallStartedEvent
    | ToolCallCompletedEvent
    | ConfirmationRequestedEvent
    | ConfirmationReceivedEvent,
    Field(discriminator="type"),
]

# ── Event registry ────────────────────────────────────────────────────────────

_EVENT_REGISTRY = {
    EventType.RUN_STARTED: RunStartedEvent,
    EventType.RUN_COMPLETED: RunCompletedEvent,
    EventType.REASONING_CHECKPOINT: ReasoningCheckpointEvent,
    EventType.FINAL_RESPONSE: FinalResponseEvent,
    EventType.SUBAGENT_INVOKED: SubagentInvokedEvent,
    EventType.TOOL_CALL_STARTED: ToolCallStartedEvent,
    EventType.TOOL_CALL_COMPLETED: ToolCallCompletedEvent,
    EventType.CONFIRMATION_REQUESTED: ConfirmationRequestedEvent,
    EventType.CONFIRMATION_RECEIVED: ConfirmationReceivedEvent,
}
