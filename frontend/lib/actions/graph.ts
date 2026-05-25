"use server";

import { GraphResponseSchema } from "@/lib/schemas/graph";
import type { GraphResponse } from "@/lib/schemas/graph";
import { API_V1_GRAPH } from "@/lib/constants";
import { API_URL } from "@/lib/config";
import { getAuthHeaders, handleErrorResponse } from "@/lib/api-utils";

export async function getGraph(): Promise<GraphResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/${API_V1_GRAPH}`, { headers });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return GraphResponseSchema.parse(await res.json());
}
