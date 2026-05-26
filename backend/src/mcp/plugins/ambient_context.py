"""Plugin that injects ambient context into MongoDB MCP tool calls.

The LLM only emits intent — it never has to predict or remember ambient
values like which tenant owns the request or which database to target.
This plugin intercepts every MongoDB MCP tool invocation and:

- Injects ``tenantId`` into filters, documents, and pipeline stages.
- Injects ``database`` forced to ``"canon"``.
- Wraps 24-char hex strings in ObjectId fields to EJSON ``$oid`` format
  so the LLM never worries about serialization.

Named by mechanism (injecting ambient context), not outcome (tenant
isolation).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from src.mcp.constants import (
    Database,
    SessionState,
    ToolName,
)

_HEX24 = re.compile(r"^[0-9a-fA-F]{24}$")

_OID_FIELDS = frozenset({"_id", "tenantId", "supersedes", "supersededBy"})
_OID_ARRAY_FIELDS = frozenset({"relatedEntityIds"})


class AmbientContextPlugin(BasePlugin):
    """Injects tenant context into MongoDB MCP tool args before execution.

    Operates on the ``before_tool_callback`` hook, mutating ``tool_args``
    in place so the tool receives the augmented arguments while the LLM
    never had to specify them.
    """

    def __init__(self) -> None:
        super().__init__(name="ambient_context")

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict | None:
        if tool.name not in ToolName.ALL:
            return None

        tenant_id = tool_context.state.get(SessionState.TENANT_ID)
        if not tenant_id:
            logging.getLogger(__name__).warning(
                "ambient_context: no tenant_id in state | tool=%s",
                tool.name,
            )
            return None

        logging.getLogger(__name__).debug(
            "ambient_context: injecting context | tool=%s tenant=%s",
            tool.name,
            tenant_id,
        )
        tool_args["database"] = Database.CANON
        self._ejsonize(tool_args)

        ejson_tenant = {"$oid": tenant_id}

        if tool.name in (ToolName.FIND, ToolName.COUNT):
            self._inject_into_filter(tool_args, ejson_tenant)

        elif tool.name == ToolName.AGGREGATE:
            max_depth = tool_context.state.get(SessionState.MAX_GRAPH_DEPTH, 2)
            self._inject_into_pipeline(tool_args, ejson_tenant, max_depth)

        elif tool.name == ToolName.INSERT_MANY:
            self._inject_into_documents(tool_args, ejson_tenant)

        elif tool.name == ToolName.UPDATE_MANY:
            self._inject_into_filter(tool_args, ejson_tenant)

        return None

    # ── EJSON auto-wrapping ──────────────────────────────────────────────────

    @staticmethod
    def _ejsonize(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                if (
                    key in _OID_FIELDS
                    and isinstance(value, str)
                    and _HEX24.match(value)
                ):
                    obj[key] = {"$oid": value}
                elif key in _OID_ARRAY_FIELDS:
                    if isinstance(value, list):
                        obj[key] = AmbientContextPlugin._ejsonize_oid_list(value)
                    elif isinstance(value, str) and _HEX24.match(value):
                        obj[key] = {"$oid": value}
                    else:
                        AmbientContextPlugin._ejsonize(value)
                else:
                    AmbientContextPlugin._ejsonize(value)
        elif isinstance(obj, list):
            for item in obj:
                AmbientContextPlugin._ejsonize(item)

    @staticmethod
    def _ejsonize_oid_list(items: list[Any]) -> list[Any]:
        return [
            {"$oid": item} if isinstance(item, str) and _HEX24.match(item) else item
            for item in items
        ]

    # ── Context injection helpers ────────────────────────────────────────────

    @staticmethod
    def _inject_into_filter(
        tool_args: dict[str, Any],
        ejson_tenant: dict[str, str],
    ) -> None:
        filt = tool_args.get("filter")
        if not isinstance(filt, dict):
            filt = {}
            tool_args["filter"] = filt
        filt["tenantId"] = ejson_tenant

    @staticmethod
    def _inject_into_documents(
        tool_args: dict[str, Any],
        ejson_tenant: dict[str, str],
    ) -> None:
        documents = tool_args.get("documents")
        if isinstance(documents, list):
            for doc in documents:
                if isinstance(doc, dict):
                    doc["tenantId"] = ejson_tenant

    @staticmethod
    def _inject_into_pipeline(
        tool_args: dict[str, Any],
        ejson_tenant: dict[str, str],
        max_depth: int = 2,
    ) -> None:
        pipeline = tool_args.get("pipeline")
        if not isinstance(pipeline, list):
            return

        for stage in pipeline:
            if not isinstance(stage, dict):
                continue

            if "$match" in stage and isinstance(stage["$match"], dict):
                stage["$match"]["tenantId"] = ejson_tenant

            if "$vectorSearch" in stage:
                vs = stage["$vectorSearch"]
                if isinstance(vs, dict):
                    if "preFilter" not in vs or not isinstance(vs["preFilter"], dict):
                        vs["preFilter"] = {}
                    vs["preFilter"]["tenantId"] = ejson_tenant

            if "$search" in stage and isinstance(stage["$search"], dict):
                search = stage["$search"]
                if "filter" not in search:
                    search["filter"] = {}
                if isinstance(search["filter"], dict):
                    search["filter"]["tenantId"] = ejson_tenant

            if "$graphLookup" in stage and isinstance(stage["$graphLookup"], dict):
                gl = stage["$graphLookup"]
                if "restrictSearchWithMatch" not in gl or not isinstance(
                    gl["restrictSearchWithMatch"], dict
                ):
                    gl["restrictSearchWithMatch"] = {}
                gl["restrictSearchWithMatch"]["tenantId"] = ejson_tenant
                if "maxDepth" not in gl:
                    gl["maxDepth"] = max_depth
