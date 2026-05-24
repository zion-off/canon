"use server";

import {
  SessionResponseSchema,
  AgentEventSchema,
  type SessionResponse,
  type AgentEvent,
} from "@/lib/schemas/sessions";
import { z } from "zod";
import { API_URL, API_V1_SESSIONS } from "@/lib/constants";
import { getAuthHeaders, handleErrorResponse } from "@/lib/api-utils";

export async function listSessions(): Promise<SessionResponse[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/${API_V1_SESSIONS}`, { headers });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return z.array(SessionResponseSchema).parse(await res.json());
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/${API_V1_SESSIONS}/${sessionId}`, { headers });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return SessionResponseSchema.parse(await res.json());
}

export async function getSessionEvents(sessionId: string): Promise<AgentEvent[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/${API_V1_SESSIONS}/${sessionId}/events`, { headers });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return z.array(AgentEventSchema).parse(await res.json());
}
