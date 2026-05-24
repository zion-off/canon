from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import get_db, jwt_auth

router = APIRouter(tags=["graph"])


@router.get("/graph")
async def get_graph(user: dict = Depends(jwt_auth), db=Depends(get_db)):
    """Full memory graph for visualization. Tenant from JWT."""
    tenant_id = user.get("tenantId")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No team associated")

    nodes = await db.memory_nodes.find(
        {"tenantId": ObjectId(tenant_id)},
        {"embedding": 0, "content": 0},
    ).to_list(length=2000)

    graph_nodes = []
    graph_links = []
    node_ids = {str(n["_id"]) for n in nodes}

    for node in nodes:
        nid = str(node["_id"])
        graph_nodes.append({
            "id": nid,
            "name": node["name"],
            "description": node.get("description", ""),
            "status": node.get("status", ""),
            "tags": node.get("tags", []),
            "supersedes": str(node["supersedes"]) if node.get("supersedes") else None,
            "supersededBy": (
                str(node["supersededBy"]) if node.get("supersededBy") else None
            ),
            "updatedAt": (
                node["updatedAt"].isoformat() if node.get("updatedAt") else None
            ),
            "createdAt": (
                node["createdAt"].isoformat() if node.get("createdAt") else None
            ),
        })
        for rel_id in node.get("relatedEntityIds", []):
            rid = str(rel_id)
            if rid in node_ids and nid < rid:
                graph_links.append({"source": nid, "target": rid, "type": "related"})
        if node.get("supersedes"):
            sid = str(node["supersedes"])
            if sid in node_ids:
                graph_links.append({"source": sid, "target": nid, "type": "supersedes"})

    return {"nodes": graph_nodes, "links": graph_links}
