from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from src.models.schemas._base import MongoModel

# ── Type alias for the discriminant field ─────────────────────────────────────

AgentEventType = Literal[
    "reasoning_checkpoint",
    "tool_call_started",
    "tool_call_completed",
    "subagent_invoked",
    "run_started",
    "run_completed",
    "final_response",
]


# ── Payload models ────────────────────────────────────────────────────────────


class RunStartedPayload(BaseModel):
    pass


class RunCompletedPayload(BaseModel):
    pass


class ReasoningCheckpointPayload(BaseModel):
    message: str


class FinalResponsePayload(BaseModel):
    text: str


class SubagentInvokedPayload(BaseModel):
    agent_name: str


class ToolCallStartedPayload(BaseModel):
    tool_name: str
    args: dict[str, Any]
    invocation_id: str


class ToolCallCompletedPayload(BaseModel):
    tool_name: str
    args: dict[str, Any]
    result: Any
    status: str
    invocation_id: str


# ── Base event ────────────────────────────────────────────────────────────────


class AgentEvent(MongoModel):
    """Envelope fields shared by every event type.

    ``type`` is intentionally absent here so subclasses can declare it as a
    ``Literal`` without triggering invariant-override errors. Every concrete
    subclass defines ``type`` and a typed ``payload``.
    Prefer ``AnyAgentEvent`` for all annotations; use this base only for
    isinstance checks and internal helpers that don't need to access ``type``.
    """

    author: str | None = None
    sequence: int | None = None
    timestamp: str | None = None
    is_final: bool = Field(
        default=False, validation_alias="isFinal", serialization_alias="isFinal"
    )


# ── Typed event subclasses ────────────────────────────────────────────────────


class RunStartedEvent(AgentEvent):
    type: Literal["run_started"] = "run_started"
    payload: RunStartedPayload = Field(default_factory=RunStartedPayload)


class RunCompletedEvent(AgentEvent):
    type: Literal["run_completed"] = "run_completed"
    payload: RunCompletedPayload = Field(default_factory=RunCompletedPayload)


class ReasoningCheckpointEvent(AgentEvent):
    type: Literal["reasoning_checkpoint"] = "reasoning_checkpoint"
    payload: ReasoningCheckpointPayload


class FinalResponseEvent(AgentEvent):
    type: Literal["final_response"] = "final_response"
    payload: FinalResponsePayload


class SubagentInvokedEvent(AgentEvent):
    type: Literal["subagent_invoked"] = "subagent_invoked"
    payload: SubagentInvokedPayload


class ToolCallStartedEvent(AgentEvent):
    type: Literal["tool_call_started"] = "tool_call_started"
    payload: ToolCallStartedPayload


class ToolCallCompletedEvent(AgentEvent):
    type: Literal["tool_call_completed"] = "tool_call_completed"
    payload: ToolCallCompletedPayload


# ── Discriminated union ───────────────────────────────────────────────────────

AnyAgentEvent = Annotated[
    RunStartedEvent
    | RunCompletedEvent
    | ReasoningCheckpointEvent
    | FinalResponseEvent
    | SubagentInvokedEvent
    | ToolCallStartedEvent
    | ToolCallCompletedEvent,
    Field(discriminator="type"),
]


# ── Document → event factory ──────────────────────────────────────────────────

_EVENT_REGISTRY: dict[str, type[AgentEvent]] = {
    "run_started": RunStartedEvent,
    "run_completed": RunCompletedEvent,
    "reasoning_checkpoint": ReasoningCheckpointEvent,
    "final_response": FinalResponseEvent,
    "subagent_invoked": SubagentInvokedEvent,
    "tool_call_started": ToolCallStartedEvent,
    "tool_call_completed": ToolCallCompletedEvent,
}


def agent_event_from_document(doc: dict[str, Any]) -> AnyAgentEvent:
    """Reconstruct a typed event from a stored MongoDB document dict.

    Handles legacy documents (pre-structured-payload) that carry ``content``
    but no ``payload``, by deriving a best-effort payload from ``content``.
    Unknown event types are surfaced as ``FinalResponseEvent`` so content is
    never silently discarded.
    """
    event_type = doc.get("type", "")
    cls = _EVENT_REGISTRY.get(event_type)

    if cls is None:
        return FinalResponseEvent.model_validate(
            {
                **doc,
                "type": "final_response",
                "payload": {"text": doc.get("content") or ""},
            }
        )

    payload = doc.get("payload") or _legacy_payload(
        event_type, doc.get("content") or ""
    )
    return cls.model_validate({**doc, "payload": payload})  # type: ignore[return-value]


def _legacy_payload(event_type: str, content: str) -> dict[str, Any]:
    """Derive a structured payload from the old plain-text ``content`` field."""
    if event_type == "reasoning_checkpoint":
        return {"message": content}
    if event_type == "final_response":
        return {"text": content}
    if event_type in {"run_started", "run_completed"}:
        return {}
    if event_type == "subagent_invoked":
        agent_name = content.removesuffix(" started") if content else ""
        return {"agent_name": agent_name}
    if event_type == "tool_call_started":
        tool_name = content.split(":")[0].strip() if ":" in content else content
        return {"tool_name": tool_name, "args": {}, "invocation_id": ""}
    if event_type == "tool_call_completed":
        tool_name = content.split("(")[0].strip() if "(" in content else content
        return {
            "tool_name": tool_name,
            "args": {},
            "result": None,
            "status": "unknown",
            "invocation_id": "",
        }
    return {}
