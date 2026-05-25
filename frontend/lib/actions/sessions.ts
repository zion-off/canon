"use server";

import { SessionResponseSchema, AgentEventSchema } from "@/lib/schemas/sessions";
import type { SessionResponse, AgentEvent } from "@/lib/schemas/sessions";
import { z } from "zod";
import { API_V1_SESSIONS } from "@/lib/constants";
import { apiFetch } from "@/lib/api-utils";

export async function listSessions(): Promise<SessionResponse[]> {
  return apiFetch(API_V1_SESSIONS, z.array(SessionResponseSchema));
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  return apiFetch(`${API_V1_SESSIONS}/${sessionId}`, SessionResponseSchema);
}

export async function getSessionEvents(sessionId: string): Promise<AgentEvent[]> {
  return apiFetch(`${API_V1_SESSIONS}/${sessionId}/events`, z.array(AgentEventSchema));
}
