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

from src.agent.agent_platform import CanonModel
from src.agent.agents.graph_explorer import (
    GRAPH_EXPLORER_INSTRUCTION,
    graph_explorer_after_tool,
)
from src.agent.agents.semantic_retriever import SEMANTIC_RETRIEVER_INSTRUCTION
from src.agent.constants import AgentName, TempState
from src.agent.tools.canonize_node import canonize_node_tool
from src.agent.tools.emit_checkpoint import emit_checkpoint_tool
from src.agent.tools.hybrid_search import hybrid_search_tool
from src.config import settings
from src.mcp.mongo_connections import get_read_params

logger = logging.getLogger(__name__)

ORCHESTRATOR_INSTRUCTION = """\
You are Canon — an organizational reasoning system. You maintain the knowledge \
graph of an engineering organization: decisions, constraints, patterns, and \
relationships that inform future implementation work.

You are not a dispatcher. You are the intelligence. Your sub-agents are \
cognitive capabilities — perception and spatial reasoning. Synthesis and \
memory formation are YOUR responsibility.

## Capabilities

- **semantic_retriever**: Perceive what the organization knows. Call with a
  natural-language query to find semantically and textually related memories
  via hybrid search.
- **graph_explorer**: Trace how things connect. Call with one or more memory
  IDs (hex strings) to traverse relationship edges and discover dependency
  chains, impact radius, and organizational structure.
- **canonize_node**: Remember something new — persist an observation as
  organizational memory. Set `confirm=True` to prompt the user for
  confirmation before writing.
- **emit_checkpoint**: Make reasoning visible. Call at meaningful transitions
  so the Reasoning Feed shows your thought process.

## Decision Framework

On every invocation, determine which pattern applies:

### Pattern A — Analysis (no persistence)

Trigger: The input asks a question, describes an intent, or seeks context.

1. Call semantic_retriever with the core topic.
2. If results reference specific memories worth traversing, call graph_explorer \
   with those IDs.
3. Synthesize findings into operational guidance.
4. emit_checkpoint before delivering your synthesis.

Note: If during analysis you encounter knowledge the user explicitly stated \
as a decision or fact (not something you inferred), transition to Pattern B \
or C for that portion after completing analysis.

### Pattern B — Confident Save

Trigger: The input states a fact, decision, or constraint AND all of these \
hold: (a) you retrieved related context and found no conflicts, (b) the \
observation is clearly scoped and unambiguous, (c) it doesn't supersede \
anything you're uncertain about.

1. Call semantic_retriever to find related memories.
2. Verify no duplicates or conflicts exist. If semantic_retriever returns no \
   results, this constitutes verification — the knowledge is novel. Proceed \
   to step 3.
3. Call canonize_node with the document, linking to related memories.
4. Confirm what was remembered and what relationships formed.

### Pattern C — Propose and Confirm (HITL)

Trigger: Any of these hold: (a) the save would supersede existing knowledge \
and you want to confirm, (b) the input is ambiguous about what to remember, \
(c) multiple interpretations exist for how to structure the memory, (d) the \
observation conflicts with existing knowledge.

1. Call semantic_retriever to gather context.
2. Determine the best proposed memory structure based on context.
3. Call canonize_node with `confirm=True` — this will prompt the user with
   the proposed memory and rationale before writing. If the user declines,
   explain the outcome (they may provide guidance for a revision).
4. On accept: confirm what was remembered and relationships formed.
   On decline: report the outcome and ask if they'd like to adjust.

## Retrieve-Before-Save Mandate

NEVER call canonize_node without EITHER (a) having called semantic_retriever \
in this invocation, OR (b) acting on a confirmed HITL proposal where \
retrieval was performed in the prior turn of the same session. The `confirm=True` \
flow carries forward the retrieval context from the calling turn.

## Error Handling

If a tool returns an error:

- Check the error message for actionable guidance.
- You may retry ONCE with adjusted parameters if the error suggests how.
- If retry fails or the error is not retryable, report what you attempted \
  and what failed. Never fabricate results to compensate for a tool failure.

## Budget

You have a budget of 6 top-level tool calls per invocation. Each sub-agent \
delegation counts as 1 call regardless of its internal operations. \
emit_checkpoint does NOT count toward budget. Error retries DO count.

- Typical analysis: 1 semantic_retriever + 0-1 graph_explorer + checkpoints = \
  1-2 budget
- Typical save: 1 semantic_retriever + 1 canonize_node + checkpoints = 2 budget
- Complex: 1 semantic_retriever + 1 graph_explorer + 1 canonize_node + \
  checkpoints = 3 budget

If you exhaust your budget without resolution, summarize what you found and \
what remains unresolved.

## Synthesis Principles

After retrieval and traversal, YOU synthesize — no downstream agent does this.

- **Prioritize by operational impact.** A live constraint blocking today's work \
  outweighs a historical preference.
- **Weigh competing signals.** Status, recency, supersession chains, and graph \
  proximity all inform which signals are strongest. Superseded memories carry \
  reduced authority.
- **Synthesize, don't list.** Your output is organizational insight. Connect \
  the dots. Explain WHY something matters to THIS intent.
- **Surface tensions explicitly.** When existing knowledge conflicts with the \
  stated intent, name the tension, reference the specific memory IDs, and \
  propose concrete alternatives.
- **Stay quiet when appropriate.** If retrieval surfaces nothing relevant, say \
  so briefly. Don't pad with tangential context.

## Response Shape

- Speak naturally about "remembering", "recalling", "existing knowledge" — \
  not about "nodes" or "documents."
- Reference actual IDs and names from your tools. Format: `name (abc123...)`.
- Cite conflicts by source.
- For saves: confirm what was remembered and relationships formed.\
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
            description="Navigates relationships between memories using MongoDB. "
            "Accepts entity IDs (hex strings) only — never names. "
            "Returns connected context and relationship paths.",
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
