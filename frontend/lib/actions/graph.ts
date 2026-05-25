"use server";

import { GraphResponseSchema } from "@/lib/schemas/graph";
import type { GraphResponse } from "@/lib/schemas/graph";
import { API_V1_GRAPH } from "@/lib/constants";
import { apiFetch } from "@/lib/api-utils";

export async function getGraph(): Promise<GraphResponse> {
  return apiFetch(API_V1_GRAPH, GraphResponseSchema);
}
