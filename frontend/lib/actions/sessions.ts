"use server";

import { cookies } from "next/headers";
import {
  SessionResponseSchema,
  AgentEventSchema,
  type SessionResponse,
  type AgentEvent,
} from "@/lib/schemas/sessions";
import { z } from "zod";
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

export async function listSessions(): Promise<SessionResponse[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/sessions`, { headers });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return z.array(SessionResponseSchema).parse(await res.json());
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/sessions/${sessionId}`, {
    headers,
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return SessionResponseSchema.parse(await res.json());
}

export async function getSessionEvents(
  sessionId: string
): Promise<AgentEvent[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/sessions/${sessionId}/events`, {
    headers,
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return z.array(AgentEventSchema).parse(await res.json());
}
