"use server";

import { cookies } from "next/headers";
import {
  GraphResponseSchema,
  type GraphResponse,
} from "@/lib/schemas/graph";
import { logout } from "@/lib/actions/auth";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const cookieStore = await cookies();
  const token = cookieStore.get("canon_token")?.value;
  if (!token) {
    throw new Error("Not authenticated");
  }
  return { Authorization: `Bearer ${token}` };
}

async function handleErrorResponse(res: Response): Promise<never> {
  if (res.status === 401) {
    await logout();
    throw new Error("Session expired");
  }
  const err = await res.json().catch(() => null);
  throw new Error(
    (err as { detail?: string } | null)?.detail ??
      `Request failed: ${res.status}`
  );
}

export async function getGraph(): Promise<GraphResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/graph`, { headers });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return GraphResponseSchema.parse(await res.json());
}
