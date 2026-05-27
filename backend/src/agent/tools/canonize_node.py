"""Canonize node tool — persists a memory node in the knowledge graph."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from beanie.odm.fields import PydanticObjectId
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.agent.agent_platform import CanonModel
from src.agent.constants import SessionState
from src.agent.models import (
    CanonizeError,
    CanonizeResult,
    CanonizeSuccess,
    MemoryNodeInput,
)
from src.agent.tools.hybrid_search import build_embedding_text
from src.config import settings
from src.models.documents import MemoryNodeDocument


async def canonize_node(
    document: MemoryNodeInput,
    rationale: str,
    reverse_link_ids: list[str],
    tool_context: ToolContext,
) -> CanonizeResult:
    """Persist an observation as a structured memory node in the knowledge graph."""
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

    try:
        tenant_oid = PydanticObjectId(tenant_id_str)
        related_entity_oids = [PydanticObjectId(rid) for rid in doc.related_entity_ids]
        related_existing_oids = [PydanticObjectId(rid) for rid in reverse_link_ids]
    except Exception as exc:
        return CanonizeError(
            error=f"Invalid ObjectId: {exc}",
            hint="Malformed ID",
            retry="Verify IDs are 24-char hex from actual query results",
        )

    supersedes_oid: PydanticObjectId | None = None
    if doc.supersedes:
        try:
            supersedes_oid = PydanticObjectId(doc.supersedes)
        except Exception as exc:
            return CanonizeError(
                error=f"Invalid ObjectId in supersedes: {exc}",
                hint="Malformed ID",
                retry="Verify IDs are 24-char hex from actual query results",
            )

    now = datetime.now(tz=UTC)
    embedding_text = build_embedding_text(doc)
    try:
        embedding = await CanonModel.embed(
            embedding_text,
            task_type="RETRIEVAL_DOCUMENT",
            model=settings.embedding_model,
        )
    except Exception as exc:
        log.warning("canonize_node: embedding failed | error=%s", exc)
        return CanonizeError(
            error=f"Embedding generation failed: {exc}",
            hint="Embedding model unavailable",
            retry="Wait and retry",
        )

    node_doc = MemoryNodeDocument(
        tenantId=tenant_oid,
        name=doc.name,
        description=doc.description,
        content=doc.content,
        status=doc.status,
        tags=doc.tags,
        metadata=doc.metadata,
        relatedEntityIds=related_entity_oids,
        supersedes=supersedes_oid,
        embeddingText=embedding_text,
        embedding=embedding,
        createdAt=now,
        updatedAt=now,
    )
    try:
        await node_doc.insert()
    except Exception as exc:
        if "duplicate key" in str(exc).lower():
            return CanonizeError(
                error=f"A node named '{doc.name}' already exists for this tenant.",
                hint="A memory with this name already exists",
                retry="Use different name or supersede existing. Retrieve it first.",
            )
        log.warning("canonize_node: insert failed | name=%s error=%s", doc.name, exc)
        return CanonizeError(
            error=f"Insert failed: {exc}",
            hint="Database write failed",
            retry="Retry once. If persistent, surface the error.",
        )

    new_id = node_doc.id
    relationships_formed = 0

    if related_existing_oids:
        await MemoryNodeDocument.find(
            {"_id": {"$in": related_existing_oids}, "tenantId": tenant_oid}
        ).update_many(
            {"$addToSet": {"relatedEntityIds": new_id}, "$set": {"updatedAt": now}}
        )
        relationships_formed += len(related_existing_oids)

    if supersedes_oid:
        await MemoryNodeDocument.find(
            {"_id": supersedes_oid, "tenantId": tenant_oid}
        ).update_many(
            {"$set": {"supersededBy": new_id, "status": "deprecated", "updatedAt": now}}
        )
        relationships_formed += 1

    log.info(
        "canonize_node: written | name=%s node_id=%s relationships=%d rationale=%.80s",
        doc.name,
        new_id,
        relationships_formed,
        rationale,
    )
    return CanonizeSuccess(
        node_id=str(new_id),
        name=doc.name,
        relationships_formed=relationships_formed,
    )


canonize_node_tool = FunctionTool(func=canonize_node)
