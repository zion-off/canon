from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from google.adk.agents import Agent
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from src.agent.agent_platform import CanonModel
from src.agent.constants import AgentName, TempState
from src.agent.tools.emit_checkpoint import emit_checkpoint_tool
from src.agent.tools.hybrid_search import hybrid_search_tool
from src.config import settings

logger = logging.getLogger(__name__)

SEMANTIC_RETRIEVER_INSTRUCTION = """\
You are Canon's perception layer. Your job is to surface what the organization
knows that bears on a query — especially anything that should redirect or
constrain how someone approaches a task.

## Protocol

1. Call ``hybrid_search`` with the query text and, when useful, explicit
   keywords.
2. Return up to 10 results to the orchestrator exactly as the tool returns them
   — _id, name, description, status, tags, and metadata.

## Writing the query for recall

- Pass explicit keywords when the query carries technical identifiers, project
  names, or acronyms that may not embed well semantically ("PROJ-123", "gRPC",
  "k8s").
- Widen the query with concepts adjacent to what was asked — alternative
  approaches, the systems involved, the names things might be recorded under.
  The org may know something relevant under wording the engineer didn't use, and
  the adjacent term is how it surfaces.
- For plain natural-language queries, omit keywords and let the tool extract
  them.

## Return everything relevant

Hand results back as-is. Do NOT filter, re-rank, or summarize — the orchestrator
synthesizes. In particular, never drop nodes for being deprecated or superseded:
the orchestrator needs the full picture, including how things used to be, to
reason about what holds now.

## On empty results

If hybrid_search returns zero results, report: "No matching memories found
for query: [query]". Do not fabricate IDs or names.

## Checkpoint

After the search completes, call ``emit_checkpoint``:
- "Found N memories for [query topic]. Top result: [name]"
- Or: "No results for [query topic]."

After emitting the checkpoint, return the results to the orchestrator as your final response and stop using tools.\
"""


async def semantic_retriever_after_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """Log semantic_retriever tool calls for observability."""
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

    if is_error:
        logger.warning(
            "tool_call: error | agent=%s tool=%s args=%s",
            tool_context.agent_name,
            tool.name,
            _summarize_tool_args(args),
        )
    else:
        logger.debug(
            "tool_call: ok | agent=%s tool=%s args=%s",
            tool_context.agent_name,
            tool.name,
            _summarize_tool_args(args),
        )
    return None


def _summarize_tool_args(args: dict[str, Any]) -> str:
    if not args:
        return "()"
    if "query" in args:
        return f"(query={str(args['query'])[:80]})"
    if "document" in args and isinstance(args["document"], dict):
        return f"(document={args['document'].get('name', '?')})"
    keys = list(args.keys())[:3]
    return "(" + ", ".join(f"{k}={str(args[k])[:40]}" for k in keys) + ")"


_semantic_retriever: Agent | None = None


def get_semantic_retriever() -> Agent:
    """Return the singleton semantic_retriever agent.

    Lazy-initialises on first call so the MCP toolset (via graph_explorer)
    does not need to be ready at import time.
    """
    global _semantic_retriever
    if _semantic_retriever is None:
        _semantic_retriever = Agent(
            name=AgentName.SEMANTIC_RETRIEVER,
            model=CanonModel.create(settings.fast_model),
            description=(
                "Perceives relevant organizational knowledge through hybrid search. "
                "Call with a query to find semantically and textually related memory nodes."
            ),
            instruction=SEMANTIC_RETRIEVER_INSTRUCTION,
            tools=[hybrid_search_tool, emit_checkpoint_tool],
            output_key="retrieval_results",
            after_tool_callback=semantic_retriever_after_tool,
        )
    return _semantic_retriever
