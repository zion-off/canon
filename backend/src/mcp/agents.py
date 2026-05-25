"""Canon ADK agent definitions.

Defines the orchestrator and its sub-agents (semantic_retriever,
graph_explorer, memory_writer) with their instructions and tool bindings.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.tool_context import ToolContext  # noqa: F401 — used by callbacks
from mcp.client.stdio import StdioServerParameters
from pydantic import BaseModel, Field

from src.config import settings
from src.mcp.constants import AgentName, TempState
from src.mcp.tools import (
    emit_checkpoint_tool,
    hybrid_search_tool,
    prepare_embedding_tool,
)

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

MEMORY_WRITER_INSTRUCTION = f"""\
You are Canon's memory formation. Your job is to convert observations into \
properly structured memory nodes and persist them.

{MEMORY_NODE_SCHEMA}

## Tools

- **prepare_embedding** — validates the document, generates a 768-dim vector.
  Returns ``document`` (ready for insertion) and ``meta`` (with relationship
  and supersession info).
- **MCP insert-many** — inserts document(s) into a collection.
- **MCP update-many** — updates documents matching a filter.
- **MCP find / aggregate / count** — read-back tools for discovery queries
  before writing.

## Write Flow

1. Build the node document with name, description, content, status, tags,
   metadata, and optionally ``supersedes`` (hex string of the node being
   replaced) and ``relatedEntityIds`` (hex strings of nodes to link to).

2. Call ``prepare_embedding`` with:
   - document: the full node
   - rationale: why this node should exist
   - related_existing_ids: existing node hex IDs to link bidirectionally

3. Insert via ``insert-many`` into collection ``"memory_nodes"`` with
   documents as a single-element array containing the returned ``document``.
   The response text contains the inserted IDs — record the first one as
   the new node's ``_id``.

4. If ``meta.related_existing_id_strs`` is non-empty, call ``update-many`` for
   each related ID to add the new node's ``_id`` to their ``relatedEntityIds``:
   filter: ``{{"_id": "<existing_id>"}}``
   update: ``{{"$addToSet": {{"relatedEntityIds": "<new_id>"}}}}``

5. If ``meta.supersedes_id_str`` is set, call ``update-many`` to deprecate:
   filter: ``{{"_id": "<superseded_id>"}}``
   update: ``{{"$set": {{"status": "deprecated", "supersededBy": "<new_id>"}}}}``

Use ``emit_checkpoint`` after step 2 (once the embedding is prepared) and
again after step 5 (once all writes and relationship updates are committed).

## Output Schema

Your structured output must include:
- ``name``: the node name
- ``description``: one-paragraph summary
- ``status``: the node's status
- ``tags``: discoverability tags
- ``node_id``: the hex ``_id`` returned from ``insert-many``
- ``relationships_formed``: number of ``update-many`` calls made (one per
  related existing ID in step 4, plus 1 if step 5 was executed)

Do NOT set embeddingText, embedding, createdAt, or updatedAt — \
prepare_embedding handles those.\
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
- **memory_writer**: Form new memories. Structures observations into \
  persistent, searchable knowledge nodes with proper relationships.
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


class MemoryNodeOutput(BaseModel):
    """Structured output from memory_writer — guarantees type-safe node data."""

    name: str = Field(description="Concise node name")
    description: str = Field(description="One-paragraph summary")
    status: str = Field(
        description="active, deprecated, in_progress, resolved, completed"
    )
    tags: list[str] = Field(description="Discoverability tags")
    node_id: str = Field(description="The persisted node's _id")
    relationships_formed: int = Field(
        description="Number of bidirectional edges created"
    )


async def log_tool_usage(
    tool: BaseTool,
    args: dict[str, Any],
    ctx: ToolContext,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    """Log tool calls across the agent hierarchy for observability.

    Signature matches AfterToolCallback: (tool, args, ctx, result).
    """
    state = ctx.state
    log_entry = {
        "tool": tool.name,
        "timestamp": datetime.now(UTC).isoformat(),
        "success": "error" not in (result if isinstance(result, dict) else {}),
    }
    logs = state.get(TempState.TOOL_LOGS, [])
    logs.append(log_entry)
    state[TempState.TOOL_LOGS] = logs
    return None


_semantic_retriever: Agent | None = None
_graph_explorer: Agent | None = None
_memory_writer: Agent | None = None
_read_toolset: McpToolset | None = None
_write_toolset: McpToolset | None = None


def _build_mongo_read_toolset() -> McpToolset:
    global _read_toolset
    if _read_toolset is not None:
        return _read_toolset
    _read_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "mongodb-mcp-server"],
                env={
                    "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri,
                    "MDB_MCP_READ_ONLY": "true",
                },
            ),
        ),
        tool_filter=["find", "aggregate", "count"],
    )
    return _read_toolset


def _build_mongo_write_toolset() -> McpToolset:
    global _write_toolset
    if _write_toolset is not None:
        return _write_toolset
    _write_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "mongodb-mcp-server"],
                env={
                    "MDB_MCP_CONNECTION_STRING": settings.mongodb_uri,
                },
            ),
        ),
        tool_filter=["insert-many", "update-many"],
    )
    return _write_toolset


def _get_semantic_retriever() -> Agent:
    global _semantic_retriever
    if _semantic_retriever is None:
        _semantic_retriever = Agent(
            name=AgentName.SEMANTIC_RETRIEVER,
            model=settings.fast_model,
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
            model=settings.fast_model,
            description="Traces relationships in the knowledge graph. Call when you need to "
            "understand what connects to a specific node — its neighbors, "
            "dependents, related knowledge, and organizational context.",
            instruction=GRAPH_EXPLORER_INSTRUCTION,
            tools=[_build_mongo_read_toolset(), emit_checkpoint_tool],
            output_key="graph_results",
            after_tool_callback=log_tool_usage,
        )
    return _graph_explorer


def _get_memory_writer() -> Agent:
    global _memory_writer
    if _memory_writer is None:
        _memory_writer = Agent(
            name=AgentName.MEMORY_WRITER,
            model=settings.reasoning_model,
            description="Crystallizes observations into structured memory nodes, resolves "
            "relationships, and persists to the knowledge graph. Call with the "
            "observation and any related context from prior retrieval.",
            instruction=MEMORY_WRITER_INSTRUCTION,
            tools=[
                _build_mongo_read_toolset(),
                _build_mongo_write_toolset(),
                prepare_embedding_tool,
                emit_checkpoint_tool,
            ],
            output_key="write_result",
            output_schema=MemoryNodeOutput,
            after_tool_callback=log_tool_usage,
        )
    return _memory_writer


def build_orchestrator() -> Agent:
    """Construct the orchestrator agent for a single request."""
    return Agent(
        name=AgentName.ORCHESTRATOR,
        model=settings.reasoning_model,
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[
            AgentTool(_get_semantic_retriever()),
            AgentTool(_get_graph_explorer()),
            AgentTool(_get_memory_writer()),
            GoogleSearchTool(),
            emit_checkpoint_tool,
        ],
    )


async def initialize_agents() -> None:
    """Initialize MCP toolsets and warm up agent singletons at startup.

    Constructs sub-agent singletons so the first real request does not
    incur initialization latency. The shared read-only MCP toolset
    persists for the container lifetime.
    """
    _get_semantic_retriever()
    _get_graph_explorer()
    _get_memory_writer()


async def cleanup_agents() -> None:
    """Close MCP subprocess connections. Called at container shutdown."""
    if _read_toolset is not None:
        await _read_toolset.close()
    if _write_toolset is not None:
        await _write_toolset.close()
