"""Central constants for the Canon MCP agent system.

Every raw string — state keys, event types, agent names, temp keys,
tool names, and database name — lives here, grouped by namespace so
the code reads naturally::

    session.state[SessionState.TENANT_ID]
    event.type = EventType.TOOL_CALL_STARTED
    agent_name = AgentName.ORCHESTRATOR
"""

from __future__ import annotations

from typing import Final


class SessionState:
    """ADK session state keys with the ``app:`` prefix."""

    TENANT_ID: Final = "app:tenant_id"
    USER_ID: Final = "app:user_id"
    ORG_NAME: Final = "app:org_name"
    SESSION_ID: Final = "app:session_id"
    RUN_ID: Final = "app:run_id"
    MAX_GRAPH_DEPTH: Final = "app:max_graph_depth"
    EMBEDDING_MODEL: Final = "app:embedding_model"


class TempState:
    """ADK session state keys with the ``temp:`` prefix."""

    CHECKPOINTS: Final = "temp:checkpoints"
    TOOL_LOGS: Final = "temp:tool_logs"


class EventType:
    """Literal values for ``AgentEvent.type``."""

    REASONING_CHECKPOINT: Final = "reasoning_checkpoint"
    TOOL_CALL_STARTED: Final = "tool_call_started"
    TOOL_CALL_COMPLETED: Final = "tool_call_completed"
    SUBAGENT_INVOKED: Final = "subagent_invoked"
    RUN_STARTED: Final = "run_started"
    RUN_COMPLETED: Final = "run_completed"
    FINAL_RESPONSE: Final = "final_response"


class AgentName:
    """Names of agents in the Canon agent hierarchy."""

    ORCHESTRATOR: Final = "canon_orchestrator"
    SEMANTIC_RETRIEVER: Final = "semantic_retriever"
    GRAPH_EXPLORER: Final = "graph_explorer"
    MEMORY_WRITER: Final = "memory_writer"


class Database:
    """MongoDB database names."""

    CANON: Final = "canon"


class Collection:
    """MongoDB collection names."""

    MEMORY_NODES: Final = "memory_nodes"
    SESSIONS: Final = "sessions"


class ToolName:
    """MongoDB MCP server tool names."""

    FIND: Final = "find"
    COUNT: Final = "count"
    AGGREGATE: Final = "aggregate"
    INSERT_MANY: Final = "insert-many"
    UPDATE_MANY: Final = "update-many"

    READ_ONLY: Final[frozenset[str]] = frozenset({FIND, AGGREGATE, COUNT})
    WRITE: Final[frozenset[str]] = frozenset({INSERT_MANY, UPDATE_MANY})
    ALL: Final[frozenset[str]] = READ_ONLY | WRITE
