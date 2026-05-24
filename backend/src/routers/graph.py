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

    nodes = await db.memory_nodes.find(
        {"tenantId": ObjectId(user.tenant_id)},
        {"embedding": 0, "content": 0},
    ).to_list(length=2000)

    graph_nodes: list[GraphNode] = []
    graph_links: list[GraphLink] = []
    node_ids = {str(n["_id"]) for n in nodes}

    for node in nodes:
        nid = str(node["_id"])
        related_ids = node.get("relatedEntityIds", [])
        graph_nodes.append(GraphNode(
            id=nid,
            name=node["name"],
            description=node.get("description", ""),
            status=node.get("status", ""),
            tags=node.get("tags", []),
            supersedes=str(node["supersedes"]) if node.get("supersedes") else None,
            superseded_by=(
                str(node["supersededBy"]) if node.get("supersededBy") else None
            ),
            updated_at=(
                node["updatedAt"].isoformat() if node.get("updatedAt") else ""
            ),
            created_at=(
                node["createdAt"].isoformat() if node.get("createdAt") else ""
            ),
            connections=len(related_ids),
        ))
        for rel_id in related_ids:
            rid = str(rel_id)
            if rid in node_ids and nid < rid:
                graph_links.append(GraphLink(source=nid, target=rid, type="related"))
        if node.get("supersedes"):
            sid = str(node["supersedes"])
            if sid in node_ids:
                graph_links.append(GraphLink(source=sid, target=nid, type="supersedes"))

    return GraphResponse(nodes=graph_nodes, links=graph_links)
