"""Canonize node tool — persists a memory node via the MongoDB MCP server."""

import logging
from datetime import UTC, datetime

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.agent.constants import Collections, Database, SessionState
from src.agent.embedding_utils import (
    EmbeddingError,
    build_embedding_text,
    generate_embedding,
)
from src.agent.models import (
    CanonizeError,
    CanonizeResult,
    CanonizeSuccess,
    MemoryNodeInput,
)
from src.config import settings
from src.mcp.provider import call_tool
from src.mcp.response import (
    extract_mcp_error_text,
    mcp_result_is_error,
)
from src.models.schemas import (
    ConfirmationRequestedEvent,
    ConfirmationRequestedPayload,
)
from src.services.event_feed import get_feed


async def canonize_node(
    document: MemoryNodeInput,
    rationale: str,
    reverse_link_ids: list[str],
    tool_context: ToolContext,
    confirm: bool = False,
) -> CanonizeResult:
    """Persist an observation as a structured memory node in the knowledge graph.

    If confirm is True, the user will be prompted to approve the memory
    before it is written. On decline, a CanonizeError is returned.

    Args:
        document: The memory node to persist (name, description, content,
            status, tags, metadata, and optionally relatedEntityIds and
            supersedes).
        rationale: Why this memory is being persisted — the reasoning
            behind the decision.
        reverse_link_ids: Entity IDs (hex strings) that should gain a
            reverse relationship pointing back to the new node.
        tool_context: The ADK tool context, providing session state
            (tenant ID). Injected by the framework.
        confirm: If True, elicit user confirmation before writing.
            Defaults to False.

    Returns:
        CanonizeSuccess with node_id, name, and relationships_formed if
        the node is written successfully, or CanonizeError with error,
        hint, and optional retry guidance on failure.
    """
    log = logging.getLogger(__name__)
    if isinstance(document, dict):
        try:
            doc = MemoryNodeInput.model_validate(document)
        except Exception as exc:
            log.warning("canonize_node: validation failed | error=%s", exc)
            return CanonizeError(
                error=f"Invalid document: {exc}",
                hint="Document schema invalid",
                retry="Check required fields: name, description, content, status",
            )
    else:
        doc = document

    tenant_id_str = tool_context.state.get(SessionState.TENANT_ID)
    if not tenant_id_str:
        return CanonizeError(
            error="No tenant context in session state.",
            hint="Missing tenant context",
        )

    oid_related: list[dict[str, str]] = []
    oid_reverse: list[dict[str, str]] = []
    oid_supersedes: dict[str, str] | None = None

    for rid in doc.related_entity_ids:
        if len(rid) != 24:
            return CanonizeError(
                error=f"Invalid ObjectId: '{rid}' is not a 24-char hex string",
                hint="Malformed ID",
                retry="Verify IDs are 24-char hex from actual query results",
            )
        oid_related.append({"$oid": rid})

    for rid in reverse_link_ids:
        if not rid:
            continue
        if len(rid) != 24:
            return CanonizeError(
                error=f"Invalid ObjectId in reverse_link: '{rid}' is not a 24-char hex string",
                hint="Malformed ID",
                retry="Verify IDs are 24-char hex from actual query results",
            )
        oid_reverse.append({"$oid": rid})

    if doc.supersedes:
        if len(doc.supersedes) != 24:
            return CanonizeError(
                error=f"Invalid ObjectId in supersedes: '{doc.supersedes}' is not a 24-char hex string",
                hint="Malformed ID",
                retry="Verify IDs are 24-char hex from actual query results",
            )
        oid_supersedes = {"$oid": doc.supersedes}

    # --- HITL confirmation ---
    if confirm:
        try:
            feed = get_feed()
            confirmation_id = f"{tool_context.state.get(SessionState.SESSION_ID)}:{tool_context.state.get(SessionState.RUN_ID)}:canonize"
            pending = await feed.request_confirmation(
                confirmation_id=confirmation_id,
                session_id=tool_context.state.get(SessionState.SESSION_ID) or "",
                run_id=tool_context.state.get(SessionState.RUN_ID) or "",
            )
            await feed.broadcast(
                tenant_id=tenant_id_str,
                user_id=tool_context.state.get(SessionState.USER_ID) or "",
                session_id=tool_context.state.get(SessionState.SESSION_ID) or "",
                run_id=tool_context.state.get(SessionState.RUN_ID) or "",
                event=ConfirmationRequestedEvent(
                    author="canonize_node",
                    payload=ConfirmationRequestedPayload(
                        confirmation_id=confirmation_id,
                        message="Persist this memory?",
                        options=["Yes", "No"],
                        title=doc.name,
                        description=doc.description,
                    ),
                ),
            )
            await pending.resolved.wait()

            if not pending.accepted:
                return CanonizeError(
                    error="Memory persistence declined by user.",
                    hint="User chose not to save this memory. Do not retry.",
                )
        except RuntimeError:
            log.warning(
                "canonize_node: confirmation protocol not available, proceeding without confirmation"
            )

    now = datetime.now(tz=UTC)
    embedding_text = build_embedding_text(doc)
    try:
        embedding = await generate_embedding(
            embedding_text,
            task_type="RETRIEVAL_DOCUMENT",
            model=settings.embedding_model,
            context_label="canonize_node",
        )
    except EmbeddingError as exc:
        return exc.as_canonize_error()

    now_iso = now.isoformat()
    insert_doc: dict[str, object] = {
        "tenantId": {"$oid": tenant_id_str},
        "name": doc.name,
        "description": doc.description,
        "content": doc.content,
        "status": doc.status,
        "tags": doc.tags,
        "relatedEntityIds": oid_related,
        "embeddingText": embedding_text,
        "embedding": embedding,
        "metadata": doc.metadata,
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }
    if oid_supersedes is not None:
        insert_doc["supersedes"] = oid_supersedes

    try:
        insert_result = await call_tool(
            "insert-many",
            {
                "collection": Collections.MEMORY_NODES,
                "database": Database.CANON,
                "documents": [insert_doc],
            },
        )
    except Exception as exc:
        error_str = str(exc).lower()
        if "duplicate" in error_str:
            return CanonizeError(
                error=f"A node named '{doc.name}' already exists for this tenant.",
                hint="A memory with this name already exists",
                retry="Use different name or supersede existing. Retrieve it first.",
            )
        log.warning("canonize_node: insert-many failed | name=%s error=%s", doc.name, exc)
        return CanonizeError(
            error=f"Insert failed: {exc}",
            hint="Database write failed",
            retry="Retry once. If persistent, surface the error.",
        )

    if mcp_result_is_error(insert_result):
        error_text = extract_mcp_error_text(insert_result)
        log.warning(
            "canonize_node: insert-many returned error | name=%s error=%s",
            doc.name,
            error_text,
        )
        if "duplicate" in error_text.lower():
            return CanonizeError(
                error=f"A node named '{doc.name}' already exists for this tenant.",
                hint="A memory with this name already exists",
                retry="Use different name or supersede existing. Retrieve it first.",
            )
        return CanonizeError(
            error=f"Insert failed: {error_text}",
            hint="Database write returned an error",
            retry="Retry once. If persistent, surface the error.",
        )

    # Extract inserted ID from MCP response
    inserted_id = _extract_inserted_id(insert_result)
    if not inserted_id:
        log.warning(
            "canonize_node: insert-many succeeded but could not extract inserted ID | name=%s",
            doc.name,
        )
        return CanonizeError(
            error="Node inserted but ID could not be extracted from MCP response. "
            "The write may have succeeded but relationship wiring was skipped.",
            hint="MCP response format unexpected — could not find insertedId",
            retry="Use find to locate the newly inserted node by name, "
            "then manually wire relationships with update-many",
        )

    oid_new = {"$oid": inserted_id}
    relationships_formed = 0

    # Wire reverse relationships
    for oid_target in oid_reverse:
        if oid_target["$oid"] == inserted_id:
            continue
        try:
            update_result = await call_tool(
                "update-many",
                {
                    "collection": Collections.MEMORY_NODES,
                    "database": Database.CANON,
                    "filter": {
                        "_id": oid_target,
                        "tenantId": {"$oid": tenant_id_str},
                    },
                    "update": {
                        "$addToSet": {"relatedEntityIds": oid_new},
                        "$set": {"updatedAt": now_iso},
                    },
                },
            )
            if not mcp_result_is_error(update_result):
                relationships_formed += 1
        except Exception as exc:
            log.warning(
                "canonize_node: reverse link update failed | target=%s error=%s",
                oid_target.get("$oid"),
                exc,
            )

    # Wire supersession
    if oid_supersedes is not None and oid_supersedes["$oid"] != inserted_id:
        try:
            supersede_result = await call_tool(
                "update-many",
                {
                    "collection": Collections.MEMORY_NODES,
                    "database": Database.CANON,
                    "filter": {
                        "_id": oid_supersedes,
                        "tenantId": {"$oid": tenant_id_str},
                    },
                    "update": {
                        "$set": {
                            "supersededBy": oid_new,
                            "status": "deprecated",
                            "updatedAt": now_iso,
                        },
                    },
                },
            )
            if not mcp_result_is_error(supersede_result):
                relationships_formed += 1
        except Exception as exc:
            log.warning(
                "canonize_node: supersede update failed | target=%s error=%s",
                oid_supersedes.get("$oid"),
                exc,
            )

    log.info(
        "canonize_node: written | name=%s node_id=%s relationships=%d rationale=%.80s",
        doc.name,
        inserted_id,
        relationships_formed,
        rationale,
    )
    return CanonizeSuccess(
        node_id=inserted_id,
        name=doc.name,
        relationships_formed=relationships_formed,
    )


def _extract_inserted_id(result: object) -> str | None:
    """Extract the first inserted document's _id from an MCP insert-many result.

    Tries structuredContent.insertedIds[0] first (EJSON {"$oid": "..."} or
    hex string), then falls back to regex on the text content.
    """
    import json
    import re

    # Primary: structuredContent.insertedIds[0]
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        ids = structured.get("insertedIds")
        if isinstance(ids, list) and ids:
            raw = ids[0]
            if isinstance(raw, dict) and "$oid" in raw:
                return str(raw["$oid"])
            if isinstance(raw, str) and len(raw) == 24:
                return raw

    # Fallback: scan text content for a 24-char hex ObjectId
    for item in getattr(result, "content", []):
        text = getattr(item, "text", "")
        if not text:
            continue
        # Try JSON parse first (some shapes embed EJSON)
        try:
            doc = json.loads(text)
            if isinstance(doc, dict):
                ids = doc.get("insertedIds")
                if isinstance(ids, list) and ids:
                    raw = ids[0]
                    if isinstance(raw, dict) and "$oid" in raw:
                        return str(raw["$oid"])
                    if isinstance(raw, str) and len(raw) == 24:
                        return raw
        except json.JSONDecodeError:
            pass
        # Regex: bare hex ObjectId in text (e.g. "Inserted IDs: abc123...")
        match = re.search(r'\b([0-9a-f]{24})\b', text)
        if match:
            return match.group(1)

    return None


canonize_node_tool = FunctionTool(func=canonize_node)
