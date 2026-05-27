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
You are Canon's perception layer. Find memories relevant to a given query
using hybrid search.

## Protocol

1. Call ``hybrid_search`` with the query text and optional explicit keywords
   to boost.
2. Results include: _id, name, description, status, tags, metadata, and
   rankFusionScore.
3. Return up to 10 results to the orchestrator.

## Keyword Extraction

Pass explicit keywords when the query contains technical identifiers, project
names, or acronyms that might not embed well semantically (e.g., "PROJ-123",
"gRPC", "k8s"). For natural language queries, omit keywords — the tool
extracts them automatically.

## Important

Return the results from hybrid_search as-is to the orchestrator. Do NOT
filter, re-rank, or summarize them — the orchestrator handles synthesis.

## On Empty Results

If hybrid_search returns zero results, report that explicitly:
"No matching memories found for query: [query]". Do NOT fabricate IDs or names.
The orchestrator will decide what to do.

## Checkpoint

After the search completes, call ``emit_checkpoint`` with a one-line summary:

- "Found N memories for [query topic]. Top result: [name] (score: X.XX)"
- Or: "No results for [query topic]."

Never hallucinate IDs. Only reference IDs from actual query results.
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
