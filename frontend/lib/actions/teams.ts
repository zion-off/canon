"use server";

import {
  CreateTeamResponseSchema,
  JoinTeamResponseSchema,
  InviteResponseSchema,
  ListTokensResponseSchema,
  CreateTokenResponseSchema,
  type CreateTeamResponse,
  type JoinTeamResponse,
  type InviteResponse,
  type ListTokensResponse,
  type CreateTokenResponse,
} from "@/lib/schemas/teams";
import { API_URL, API_V1_TEAMS } from "@/lib/constants";
import { getAuthHeaders, handleErrorResponse, setAuthCookie } from "@/lib/api-utils";

export async function createTeam(name: string): Promise<{ rawApiToken: string; team: CreateTeamResponse["team"] }> {
  const headers = await getAuthHeaders(true);
  const res = await fetch(`${API_URL}${API_V1_TEAMS}/create`, {
    method: "POST",
    headers,
    body: JSON.stringify({ name }),
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  const data = CreateTeamResponseSchema.parse(await res.json());
  await setAuthCookie(data.token);

  return { rawApiToken: data.rawApiToken, team: data.team };
}

export async function joinTeam(code: string): Promise<{ team: JoinTeamResponse["team"] }> {
  const headers = await getAuthHeaders(true);
  const res = await fetch(`${API_URL}/api/v1/teams/join`, {
    method: "POST",
    headers,
    body: JSON.stringify({ code }),
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  const data = JoinTeamResponseSchema.parse(await res.json());
  await setAuthCookie(data.token);

  return { team: data.team };
}

export async function createInvite(): Promise<InviteResponse> {
  const headers = await getAuthHeaders(true);
  const res = await fetch(`${API_URL}${API_V1_TEAMS}/invite`, {
    method: "POST",
    headers,
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return InviteResponseSchema.parse(await res.json());
}

export async function listTokens(): Promise<ListTokensResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/teams/tokens`, { headers });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return ListTokensResponseSchema.parse(await res.json());
}

export async function createToken(label: string): Promise<CreateTokenResponse> {
  const headers = await getAuthHeaders(true);
  const res = await fetch(`${API_URL}/api/v1/teams/tokens`, {
    method: "POST",
    headers,
    body: JSON.stringify({ label }),
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return CreateTokenResponseSchema.parse(await res.json());
}
