from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import jwt_auth
from src.models.documents import MemoryNodeDocument
from src.models.schemas import GraphLink, GraphNode, GraphResponse, JwtPayload

router = APIRouter(tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
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
