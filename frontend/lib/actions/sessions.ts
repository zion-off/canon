"use server";

import {
  SessionResponseSchema,
  SessionListResponseSchema,
  AgentEventSchema,
} from "@/lib/schemas/sessions";
import type { SessionResponse, SessionListResponse, AgentEvent } from "@/lib/schemas/sessions";
import { z } from "zod";
import { API_V1_SESSIONS } from "@/lib/constants";
import { apiFetch } from "@/lib/api-utils";

export async function listSessions(before?: string): Promise<SessionListResponse> {
  const url = before ? `${API_V1_SESSIONS}?before=${encodeURIComponent(before)}` : API_V1_SESSIONS;
  return apiFetch(url, SessionListResponseSchema);
}

export async function listMySessions(before?: string): Promise<SessionListResponse> {
  const params = new URLSearchParams({ scope: "me" });
  if (before) params.set("before", before);
  return apiFetch(`${API_V1_SESSIONS}?${params}`, SessionListResponseSchema);
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  return apiFetch(`${API_V1_SESSIONS}/${sessionId}`, SessionResponseSchema);
}

export async function getSessionEvents(sessionId: string): Promise<AgentEvent[]> {
  return apiFetch(`${API_V1_SESSIONS}/${sessionId}/events`, z.array(AgentEventSchema));
}
