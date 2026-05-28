"use server";

import { GraphNodeSchema, GraphResponseSchema, type UpdateNodeRequest } from "@/lib/schemas/graph";
import type { GraphNode, GraphResponse } from "@/lib/schemas/graph";
import { API_V1_GRAPH } from "@/lib/constants";
import { apiFetch } from "@/lib/api-utils";

export async function getGraph(): Promise<GraphResponse> {
  return apiFetch(API_V1_GRAPH, GraphResponseSchema);
}

export async function updateNode(nodeId: string, data: UpdateNodeRequest): Promise<GraphNode> {
  return apiFetch(`${API_V1_GRAPH}/${nodeId}`, GraphNodeSchema, {
    method: "PATCH",
    body: data,
  });
}
