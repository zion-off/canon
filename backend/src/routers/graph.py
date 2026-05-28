from __future__ import annotations

from datetime import UTC, datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from src.agent.agent_platform import CanonModel
from src.agent.embedding_utils import build_embedding_text
from src.config import settings
from src.dependencies import jwt_auth
from src.models.documents import MemoryNodeDocument
from src.models.schemas import (
    GraphLink,
    GraphNode,
    GraphResponse,
    JwtPayload,
    UpdateNodeRequest,
    UpdateNodeResponse,
)

router = APIRouter(tags=["graph"])


@router.get("", response_model=GraphResponse)
async def get_graph(
    user: JwtPayload = Depends(jwt_auth),
) -> GraphResponse:
    """Full memory graph for visualization. Tenant from JWT."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="No team associated")

    tenant_oid = ObjectId(user.tenant_id)
    nodes = await MemoryNodeDocument.find(
        MemoryNodeDocument.tenant_id == tenant_oid
    ).to_list(length=2000)

    graph_links: list[GraphLink] = []
    node_ids: set[str] = set()

    graph_nodes: list[GraphNode] = []
    for node in nodes:
        data = node.model_dump(by_alias=True)
        data["connections"] = len(data.get("relatedEntityIds", []))
        graph_nodes.append(GraphNode.model_validate(data))
        node_ids.add(str(data["_id"]))

    for node in nodes:
        nid = str(node.id)
        for rel_id in node.related_entity_ids:
            rid = str(rel_id)
            if rid in node_ids and nid < rid:
                graph_links.append(GraphLink(source=nid, target=rid, type="related"))
        if node.supersedes:
            sid = str(node.supersedes)
            if sid in node_ids:
                graph_links.append(GraphLink(source=sid, target=nid, type="supersedes"))

    return GraphResponse(nodes=graph_nodes, links=graph_links)


@router.patch("/{node_id}", response_model=UpdateNodeResponse)
async def update_node(
    node_id: str,
    body: UpdateNodeRequest,
    user: JwtPayload = Depends(jwt_auth),
) -> UpdateNodeResponse:
    """Update an existing memory node and regenerate its embedding.

    Only name, description, content, status, and tags are editable.
    Supersedes/superseded_by are locked — they're managed by the canonicity model.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="No team associated")

    tenant_oid = ObjectId(user.tenant_id)

    node = await MemoryNodeDocument.get(node_id)
    if node is None or node.tenant_id != tenant_oid:
        raise HTTPException(status_code=404, detail="Node not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, value in updates.items():
        setattr(node, field, value)

    embedding_text = build_embedding_text(
        {
            "name": node.name,
            "status": node.status,
            "description": node.description or "",
            "content": node.content or "",
            "tags": node.tags,
        }
    )
    embedding = await CanonModel.embed(
        embedding_text,
        task_type="RETRIEVAL_DOCUMENT",
        model=settings.embedding_model,
    )
    node.embedding_text = embedding_text
    node.embedding = embedding
    node.updated_at = datetime.now(tz=UTC)

    await node.save()

    data = node.model_dump(by_alias=True)
    data["connections"] = len(data.get("relatedEntityIds", []))
    return UpdateNodeResponse.model_validate(data)
