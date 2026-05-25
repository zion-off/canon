from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dependencies import get_db, jwt_auth
from src.models.schemas import GraphLink, GraphNode, GraphResponse, JwtPayload

router = APIRouter(tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    user: JwtPayload = Depends(jwt_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> GraphResponse:
    """Full memory graph for visualization. Tenant from JWT."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="No team associated")

    tenant_oid = ObjectId(user.tenant_id)
    nodes = await db.memory_nodes.find(
        {"tenantId": tenant_oid},
        {"embedding": 0, "content": 0},
    ).to_list(length=2000)

    graph_links: list[GraphLink] = []
    node_ids: set[str] = set()

    graph_nodes: list[GraphNode] = []
    for node in nodes:
        node["connections"] = len(node.get("relatedEntityIds", []))
        graph_nodes.append(GraphNode.model_validate(node))
        node_ids.add(str(node["_id"]))

    for node in nodes:
        nid = str(node["_id"])
        for rel_id in node.get("relatedEntityIds", []):
            rid = str(rel_id)
            if rid in node_ids and nid < rid:
                graph_links.append(GraphLink(source=nid, target=rid, type="related"))
        if node.get("supersedes"):
            sid = str(node["supersedes"])
            if sid in node_ids:
                graph_links.append(GraphLink(source=sid, target=nid, type="supersedes"))

    return GraphResponse(nodes=graph_nodes, links=graph_links)
