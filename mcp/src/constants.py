"""Central string constants for the Canon MCP server.

Mirrors the naming conventions used in ``backend/src/agent/constants.py``.
Every raw string that represents a domain concept lives here, grouped by
namespace so the code reads naturally.
"""

from __future__ import annotations

from typing import Final


class SSEField:
    """Server-Sent Events  wire-format field names."""

    ID: Final = "id"
    EVENT: Final = "event"
    DATA: Final = "data"


class EventType:
    """Literal values for ``AgentEvent.type`` events consumed from the backend SSE stream."""

    REASONING_CHECKPOINT: Final = "reasoning_checkpoint"
    TOOL_CALL_STARTED: Final = "tool_call_started"
    TOOL_CALL_COMPLETED: Final = "tool_call_completed"
    CONFIRMATION_REQUESTED: Final = "confirmation_requested"
    FINAL_RESPONSE: Final = "final_response"


class EventPayload:
    """JSON payload keys shared between the backend agent events and MCP request/response bodies."""

    TYPE: Final = "type"
    PAYLOAD: Final = "payload"
    MESSAGE: Final = "message"
    REQUEST: Final = "request"
    CONTEXT: Final = "context"
    SESSION_ID: Final = "sessionId"
    TENANT_ID: Final = "tenantId"
    RUN_ID: Final = "runId"
    TOOL_NAME: Final = "toolName"
    STATUS: Final = "status"
    CONFIRMATION_ID: Final = "confirmationId"
    OPTIONS: Final = "options"
    TITLE: Final = "title"
    DESCRIPTION: Final = "description"
    TEXT: Final = "text"
    ACCEPTED: Final = "accepted"


class ToolCallStatus:
    """Normalized status values emitted in tool_call_completed events."""

    OK: Final = "ok"
    ERROR: Final = "error"


class ToolName:
    """MCP tool names registered by this server."""

    CANON: Final = "canon"


class APIRoute:
    """Backend REST endpoint paths.

    Format strings (``SESSION_STREAM``, ``CONFIRM``, ``HARNESS_SESSION_STREAM``)
    must be formatted with keyword arguments at the call site::

        APIRoute.SESSION_STREAM.format(session_id=...)
    """

    AGENT_RUN: Final = "/api/v1/agent/run"
    CONFIRM: Final = "/api/v1/agent/confirm/{confirmation_id}"
    PROMPTS: Final = "/api/v1/prompts"
    RESOURCES: Final = "/api/v1/resources"


class HttpHeader:
    """HTTP header field names."""

    AUTHORIZATION: Final = "Authorization"


class AuthScheme:
    """HTTP Authorization header scheme prefixes."""

    BEARER: Final = "Bearer"


class QueryParam:
    """HTTP query parameter names."""

    LAST_EVENT_ID: Final = "last_event_id"


class Elicit:
    """Values used with ``fastmcp_ctx.elicit()``."""

    ACCEPT_ACTION: Final = "accept"
    DEFAULT_REJECT: Final = "No"


class PromptName:
    """Prompt names registered with FastMCP."""

    BEFORE_IMPLEMENTING: Final = "before-implementing"
    REFLECT_SESSION: Final = "reflect-session"
    REMEMBER_DECISION: Final = "remember-decision"


class ResourceURI:
    """Resource URIs registered with FastMCP."""

    ORG_MOMENTUM: Final = "canon://org/momentum"
    ORG_STATE: Final = "canon://org/state"


class ResourcePath:
    """Backend resource path segments (used in API URLs)."""

    ORG_MOMENTUM: Final = "org-momentum"
    ORG_STATE: Final = "org-state"
