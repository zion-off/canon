"""Plugin that injects ambient context (tenant ID, database name) into
MongoDB MCP tool calls, and auto-wraps ObjectId hex strings into EJSON
``$oid`` format.

The LLM only emits intent — it never has to predict or remember ambient
values like which tenant owns the request or which database to target.
This plugin intercepts every MongoDB MCP tool invocation and:

- Injects ``tenantId`` into filters, documents, and pipeline stages.
- Injects ``database`` forced to ``"canon"``.
- Wraps 24-char hex strings in ObjectId fields to ``{"$oid": "<hex>"}``
  so the LLM never worries about EJSON serialization.

Named by mechanism (injecting ambient context), not outcome (tenant
isolation).
"""

from __future__ import annotations

import re
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# 24-character hex string pattern (MongoDB ObjectId / BSON ObjectId).
_HEX24 = re.compile(r"^[0-9a-fA-F]{24}$")

# Fields whose values should be wrapped in {"$oid": "<hex>"} when they
# appear as 24-char hex strings.
_OID_FIELDS = frozenset(
    {
        "_id",
        "tenantId",
        "supersedes",
        "supersededBy",
    }
)

# Fields whose values (or list-element values) are 24-char hex strings that
# should be wrapped in EJSON $oid format.
_OID_ARRAY_FIELDS = frozenset(
    {
        "relatedEntityIds",
    }
)


class AmbientContextPlugin(BasePlugin):
    """Injects tenant context into MongoDB MCP tool args before execution.

    Operates on the ``before_tool_callback`` hook, mutating ``tool_args``
    in place so the tool receives the augmented arguments while the LLM
    never had to specify them.
    """

    def __init__(self) -> None:
        super().__init__(name="ambient_context")
        self._mongo_tools = frozenset(
            {
                "find",
                "aggregate",
                "count",
                "insert-many",
                "update-many",
            }
        )

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> dict | None:
        if tool.name not in self._mongo_tools:
            return None

        tenant_id = tool_context.state.get("app:tenant_id")
        if not tenant_id:
            return None

        # Force database to "canon".
        tool_args["database"] = "canon"

        # Auto-wrap hex strings in ObjectId fields to EJSON $oid format.
        self._ejsonize(tool_args)

        ejson_tenant = {"$oid": tenant_id}

        if tool.name in ("find", "count"):
            self._inject_into_filter(tool_args, ejson_tenant)

        elif tool.name == "aggregate":
            max_depth = tool_context.state.get("app:max_graph_depth", 2)
            self._inject_into_pipeline(tool_args, ejson_tenant, max_depth)

        elif tool.name == "insert-many":
            self._inject_into_documents(tool_args, ejson_tenant)

        elif tool.name == "update-many":
            self._inject_into_filter(tool_args, ejson_tenant)

        return None

    # ── EJSON auto-wrapping ──────────────────────────────────────────────────

    @staticmethod
    def _ejsonize(obj: Any) -> None:
        """Walk the object tree in place and wrap 24-char hex strings in
        ObjectId-keyed fields to EJSON ``{"$oid": "<hex>"}`` format.

        The LLM passes plain hex strings for IDs. This method converts them
        before they reach the MongoDB MCP server.
        """
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                if (
                    key in _OID_FIELDS
                    and isinstance(value, str)
                    and _HEX24.match(value)
                ):
                    obj[key] = {"$oid": value}
                elif key in _OID_ARRAY_FIELDS and isinstance(value, list):
                    obj[key] = AmbientContextPlugin._ejsonize_oid_list(value)
                else:
                    AmbientContextPlugin._ejsonize(value)
        elif isinstance(obj, list):
            for item in obj:
                AmbientContextPlugin._ejsonize(item)

    @staticmethod
    def _ejsonize_oid_list(items: list[Any]) -> list[Any]:
        """Convert a list of 24-char hex strings to EJSON ``$oid`` objects."""
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
        """Inject tenantId into a MongoDB filter."""
        filt = tool_args.get("filter")
        if isinstance(filt, dict):
            filt["tenantId"] = ejson_tenant

    @staticmethod
    def _inject_into_documents(
        tool_args: dict[str, Any],
        ejson_tenant: dict[str, str],
    ) -> None:
        """Inject tenantId into every document in an insert-many payload."""
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
        """Inject ambient context into an aggregation pipeline.

        Handles injection points:
        1. ``$match`` stages — inject ``tenantId`` into the match expression.
        2. ``$vectorSearch`` stages — inject ``tenantId`` into ``preFilter``.
        3. ``$search`` stages — inject ``tenantId`` into ``filter``.
        4. ``$graphLookup`` stages — inject ``tenantId`` into
           ``restrictSearchWithMatch`` and ``maxDepth`` unless already set.
        """
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
                # Inject maxDepth from state if not already set.
                if "maxDepth" not in gl:
                    gl["maxDepth"] = max_depth
