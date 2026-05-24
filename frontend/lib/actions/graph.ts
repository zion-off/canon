"use server";

import { GraphResponseSchema, type GraphResponse } from "@/lib/schemas/graph";
import { API_URL, getAuthHeaders, handleErrorResponse } from "@/lib/api-utils";

export async function getGraph(): Promise<GraphResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/graph`, { headers });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return GraphResponseSchema.parse(await res.json());
}
