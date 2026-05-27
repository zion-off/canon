"""Canon ADK agent definitions.

Defines the orchestrator and its sub-agents (semantic_retriever, graph_explorer)
with their instructions and tool bindings. Memory persistence is handled directly
by the orchestrator via the canonize_node FunctionTool.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.tool_context import ToolContext  # noqa: F401 — used by callbacks

from src.config import settings
from src.mcp.agent_platform import CanonModel
from src.mcp.constants import AgentName, TempState
from src.mcp.mongo_connections import get_read_params
from src.mcp.tools import (
    canonize_node_tool,
    emit_checkpoint_tool,
    hybrid_search_tool,
)

logger = logging.getLogger(__name__)

MEMORY_NODE_SCHEMA = """\
## Memory Node Schema (memory_nodes collection)

The ``MemoryNode`` Pydantic model describes the full schema — its JSON
schema is sent to the LLM as the tool input definition, so this section
is just a quick reference.

- name, description, content, status, tags, relatedEntityIds, supersedes,
  metadata"""

SEMANTIC_RETRIEVER_INSTRUCTION = f"""\
You are Canon's perception layer. Find memory nodes relevant to the given query \
using hybrid search.

{MEMORY_NODE_SCHEMA}

## Query Strategy

1. Call ``hybrid_search`` with the query text (and optional explicit keywords)
   to perform a hybrid search combining:
   - Semantic vector search on the embedding field (weighted 1.5x)
   - Keyword search on name, description, content fields (weighted 1.0x)
2. The results include _id, name, description, status, tags, metadata, and rankFusionScore.
3. Return up to 10 results.

Use ``emit_checkpoint`` after the search completes, describing what
query patterns were matched and the distribution of results.

Never hallucinate node IDs. Only reference IDs from actual query results.\
"""

GRAPH_EXPLORER_INSTRUCTION = f"""\
You are Canon's spatial reasoning — you trace how things connect in the \
organizational knowledge graph.

{MEMORY_NODE_SCHEMA}

## Query Strategy

1. Identify named entities or recognizable terms from the input (proper nouns, \
   technical terms, project names, or any identifiable organizational concept).
2. Find matching nodes using a find query with case-insensitive regex or \
   text search.
   If exact names do not match, try partial matches or search by tags.
3. From found nodes, run $graphLookup:
   - startWith: $relatedEntityIds
   - connectFromField: relatedEntityIds
   - connectToField: _id
   - depthField: hops
4. Project: _id, name, description, status, tags, metadata, supersedes, \
   supersededBy, and connected nodes with hops.
5. Return the full traversal results.

Use ``emit_checkpoint`` after the graph traversal completes, summarizing
the number of nodes found and the depth of connections discovered.

If no identifiable entities are found or no matching nodes exist, report that \
explicitly and return empty results. Do not fabricate node IDs.\
"""


ORCHESTRATOR_INSTRUCTION = """\
You are Canon — an organizational reasoning system. You hold the operational \
knowledge graph of an engineering organization and use it to think about \
implementation intents, surface conflicts, trace relationships, and form \
new memories when knowledge worth remembering emerges from conversation.

You are not a dispatcher. You are the intelligence. Your subagents are \
cognitive capabilities — perception, spatial reasoning, memory formation — \
not departments to coordinate.

## Capabilities

- **semantic_retriever**: Perceive what the organization knows about a topic. \
  Finds relevant knowledge through hybrid semantic and keyword search.
- **graph_explorer**: Trace how things connect. Follows relationships between \
  nodes to understand dependencies, impact, and organizational structure.
- **canonize_node**: Persist an observation as a memory node. Call with the \
  document (name, description, content, status, tags, metadata, and optionally \
  relatedEntityIds and supersedes), your rationale, and any related existing \
  node IDs to link bidirectionally. Returns node_id and relationships_formed.
- **emit_checkpoint**: Make your reasoning visible. Marks milestones so the \
  Reasoning Feed shows how you arrived at your conclusions.

## How to Think

For any input, reason about what you need to know and use your capabilities \
accordingly. There is no rigid protocol — use judgment:

- If someone describes an implementation intent, perceive what the organization \
  already knows about it. Trace connections if entities are named. Synthesize \
  what you find — identify conflicts, surface relevant context, recommend \
  alternatives where the intent collides with organizational state.
- If someone shares an observation worth remembering, perceive related existing \
  knowledge first (so you can form proper relationships), then crystallize the \
  observation into memory.
- You may combine analysis and persistence in a single pass if warranted.

Emit checkpoints at meaningful reasoning transitions — after perceiving relevant \
context, after tracing connections, before forming conclusions.

## Synthesis and Prioritization

You carry the full reasoning responsibility. After retrieval and graph \
traversal, YOU synthesize — no downstream agent does this for you. \
Apply these principles:

- **Prioritize by operational impact.** A live constraint blocking today's work \
  outweighs a historical preference. An active migration colliding with the \
  intent outweighs a tangentially related convention.
- **Weigh competing signals.** Retrieved nodes may disagree with each other. \
  Superseded nodes may contain outdated guidance. Status, recency, supersession \
  chains, and graph proximity all inform which signals are strongest.
- **Synthesize, don't list.** Your output is organizational insight, not a \
  dump of retrieved nodes. Connect the dots. Explain WHY something matters to \
  THIS intent. Draw the conclusion the engineer needs.
- **Surface tensions explicitly.** When retrieved knowledge conflicts with the \
  stated intent, name the tension clearly. Reference the specific nodes. \
  Propose concrete alternatives — not generic advice.
- **Know when to stay quiet.** If retrieval surfaces nothing relevant, say so \
  briefly. Don't pad responses with tangential context to appear useful.

## Response Shape

Be operationally specific. Reference the actual nodes and relationships you found. \
Cite conflicts by source. Propose concrete alternatives, not generic advice. \
For saves, confirm what was persisted and what relationships were established.

Never fabricate information not sourced from your capabilities.\
"""


async def log_tool_usage(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """Log tool calls across the agent hierarchy for observability."""
    state = tool_context.state
    is_error = "error" in (tool_response if isinstance(tool_response, dict) else {})
    log_entry = {
        "tool": tool.name,
        "timestamp": datetime.now(UTC).isoformat(),
        "success": not is_error,
    }
    logs = state.get(TempState.TOOL_LOGS, [])
    logs.append(log_entry)
    state[TempState.TOOL_LOGS] = logs

    log = logging.getLogger(__name__)
    if is_error:
        log.warning(
            "tool_call: error | agent=%s tool=%s args=%s",
            tool_context.agent_name,
            tool.name,
            _summarize_tool_args(args),
        )
    else:
        log.debug(
            "tool_call: ok | agent=%s tool=%s args=%s",
            tool_context.agent_name,
            tool.name,
            _summarize_tool_args(args),
        )
    return None


def _summarize_tool_args(args: dict[str, Any]) -> str:
    """Produce a brief summary of tool args for logging."""
    if not args:
        return "()"
    if "query" in args:
        return f"(query={str(args['query'])[:80]})"
    if "document" in args and isinstance(args["document"], dict):
        return f"(document={args['document'].get('name', '?')})"
    keys = list(args.keys())[:3]
    return "(" + ", ".join(f"{k}={str(args[k])[:40]}" for k in keys) + ")"


async def graph_explorer_after_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: Any,
) -> Any | None:
    """Observe graph_explorer tool responses for error patterns."""
    # Delegate to shared tool-usage logging first
    await log_tool_usage(tool, args, tool_context, tool_response)

    response_str = str(tool_response) if tool_response else ""
    if "error" in response_str.lower() or "Error" in response_str:
        logger.warning(
            "graph_explorer tool '%s' returned error-like response: %.200s",
            tool.name,
            response_str,
        )
    return None  # Don't modify the response


_semantic_retriever: Agent | None = None
_graph_explorer: Agent | None = None
_read_toolset: McpToolset | None = None


def _build_mongo_read_toolset() -> McpToolset:
    global _read_toolset
    if _read_toolset is not None:
        return _read_toolset
    _read_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=get_read_params(),
        ),
        tool_filter=["find", "aggregate", "count"],
    )
    return _read_toolset


def _get_semantic_retriever() -> Agent:
    global _semantic_retriever
    if _semantic_retriever is None:
        _semantic_retriever = Agent(
            name=AgentName.SEMANTIC_RETRIEVER,
            model=CanonModel.create(settings.fast_model),
            description="Perceives relevant organizational knowledge through hybrid search. "
            "Call with a query to find semantically and textually related memory nodes.",
            instruction=SEMANTIC_RETRIEVER_INSTRUCTION,
            tools=[hybrid_search_tool, emit_checkpoint_tool],
            output_key="retrieval_results",
            after_tool_callback=log_tool_usage,
        )
    return _semantic_retriever


def _get_graph_explorer() -> Agent:
    global _graph_explorer
    if _graph_explorer is None:
        _graph_explorer = Agent(
            name=AgentName.GRAPH_EXPLORER,
            model=CanonModel.create(settings.fast_model),
            description="Traces relationships in the knowledge graph. Call when you need to "
            "understand what connects to a specific node — its neighbors, "
            "dependents, related knowledge, and organizational context.",
            instruction=GRAPH_EXPLORER_INSTRUCTION,
            tools=[_build_mongo_read_toolset(), emit_checkpoint_tool],
            output_key="graph_results",
            after_tool_callback=graph_explorer_after_tool,
        )
    return _graph_explorer


def build_orchestrator() -> Agent:
    """Construct the orchestrator agent for a single request."""
    tools: list = [
        AgentTool(_get_semantic_retriever()),
        AgentTool(_get_graph_explorer()),
        canonize_node_tool,
        emit_checkpoint_tool,
    ]
    if False and settings.reasoning_model.startswith("gemini"):  # noqa: SIM223
        tools.append(GoogleSearchTool())

    return Agent(
        name=AgentName.ORCHESTRATOR,
        model=CanonModel.create(settings.reasoning_model),
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=tools,
    )


async def initialize_agents() -> None:
    """Initialize MCP toolsets and warm up agent singletons at startup.

    Constructs sub-agent singletons so the first real request does not
    incur initialization latency. The shared read-only MCP toolset
    persists for the container lifetime.
    """
    _get_semantic_retriever()
    _get_graph_explorer()


async def cleanup_agents() -> None:
    """Close MCP subprocess connections. Called at container shutdown."""
    if _read_toolset is not None:
        await _read_toolset.close()
