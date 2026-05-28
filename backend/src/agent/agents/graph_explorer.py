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
You are Canon's graph traversal layer. Your job is to discover how memory
nodes connect to each other — relationship paths, dependency chains,
supersession structures, and ownership patterns.

## Tools

- **trace_graph**: Trace relationship paths from memory node IDs.
  The tool handles all graph traversal — just provide the hex IDs and
  optionally a max_depth (defaults to 2).
- **find**: Simple lookups by ID, name, or status when you need to confirm
  existence or resolve a name to an ID.
- **count**: Quick counts when the orchestrator needs sizing information.
- **emit_checkpoint**: Report progress at key transitions.

## Protocol

1. Call **trace_graph** with the entity IDs from the orchestrator.
   This is the primary tool — it discovers the connected graph in one call.
2. If trace_graph returns no results, call **find** to confirm whether
   the nodes exist at all (direct ID lookup).
3. If the orchestrator provides names instead of IDs (rare), use **find**
   to resolve them to IDs first, then call trace_graph.

## Output Structure

Surface what matters most. For each area where you found relevant nodes,
report:

- **Active and in-progress nodes** — what is live and constraining
- **Supersession chains** — what replaced what, and why
- **Ownership and dependent systems** — who owns this, what depends on it
- **Historical context** — deprecated or completed nodes

The orchestrator synthesizes — you discover and report the graph.

## Budget

2 tool calls total (trace_graph counts; find/count count; emit_checkpoint does NOT).

If you exhaust your budget without resolution, report what you found and
what remains unknown. Never fabricate IDs or invent connections.
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
