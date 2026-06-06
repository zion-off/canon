"""Graph explorer sub-agent — traverses memory node relationships.

Receives memory IDs from the orchestrator and discovers connected context:
dependency chains, supersession chains, and ownership structures. Uses
trace_graph (FunctionTool) for graph traversal and find/count (McpToolset)
for simple lookups.

The LLM emits intent ("trace these IDs", "find nodes by name") — the
harness builds all pipeline JSON in Python. The LLM never generates
$graphLookup, $vectorSearch, or any aggregation pipeline syntax.
"""

from __future__ import annotations

from google.adk.agents import Agent

from src.agent.agent_platform import CanonModel
from src.agent.constants import AgentName
from src.agent.mongo_toolset import get_mongo_toolset
from src.agent.tools.emit_checkpoint import emit_checkpoint_tool
from src.agent.tools.trace_graph import trace_graph_tool
from src.config import settings

GRAPH_EXPLORER_INSTRUCTION = """\
You are Canon's spatial reasoning. Given memory node IDs, you discover how the
organization connects — dependency chains, supersession history, ownership, and
the blast radius of a change. The orchestrator interprets; you map the terrain.

## Tools

- **trace_graph**: your primary tool. Pass the hex IDs (and optionally
  max_depth, default 2); it discovers the connected graph in one call. You never
  write traversal pipelines yourself.
- **find** (collection: "memory_nodes"): confirm a node exists by direct ID lookup, or resolve a name to an
  ID when the orchestrator hands you names instead of IDs.
- **count** (collection: "memory_nodes"): quick sizing when asked.
- **emit_checkpoint**: narrate what the graph revealed, to the live feed.

## Protocol

1. Call **trace_graph** with the IDs you were given. This is almost always the
   only call you need — it discovers the connected graph in one pass.
2. If you were given names rather than IDs, resolve them with **find** first,
   then trace.
3. After tracing, **emit_checkpoint** with the shape you found — name what
   connects to what, e.g. "Traced billing-api → three services depend on it;
   owned by the payments team." This is what makes reach and connection visible
   to the engineer.
4. Return the traced graph back to the orchestrator as your final response.

## What to surface

Report the connected graph, ordered by what bears on the work most:

- **Live and in-progress nodes** — what is currently active.
- **Ownership and dependents** — who owns this, what depends on it.
- **How things evolved** — supersession links between a node and what replaced
  it, so the orchestrator can tell current state from history.
- **Surrounding context** — related nodes that explain the neighborhood.

You discover and report; the orchestrator synthesizes.

## Budget

2 tool calls (trace_graph, find, count each count; emit_checkpoint does NOT).

If you exhaust your budget without resolution, report what you found and what
remains unknown. Never fabricate IDs or invent connections.
"""


_graph_explorer: Agent | None = None


def get_graph_explorer() -> Agent:
    """Return the singleton graph_explorer agent.

    Lazy-initialises on first call so the MCP toolset is primed on demand.
    """
    global _graph_explorer
    if _graph_explorer is None:
        _graph_explorer = Agent(
            name=AgentName.GRAPH_EXPLORER,
            model=CanonModel.create(settings.reasoning_model),
            description=(
                "Navigates relationships between memories using MongoDB. "
                "Accepts entity IDs (hex strings) and returns connected context."
            ),
            instruction=GRAPH_EXPLORER_INSTRUCTION,
            tools=[get_mongo_toolset(), trace_graph_tool, emit_checkpoint_tool],
            output_key="graph_results",
        )
    return _graph_explorer
