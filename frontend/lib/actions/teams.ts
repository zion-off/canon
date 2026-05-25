"use server";

import {
  CreateTeamResponseSchema,
  JoinTeamResponseSchema,
  InviteResponseSchema,
  ListTokensResponseSchema,
  CreateTokenResponseSchema,
} from "@/lib/schemas/teams";
import type {
  CreateTeamResponse,
  JoinTeamResponse,
  InviteResponse,
  ListTokensResponse,
  CreateTokenResponse,
} from "@/lib/schemas/teams";
import { API_V1_TEAMS } from "@/lib/constants";
import { apiFetch, setAuthCookie } from "@/lib/api-utils";

export async function createTeam(
  name: string,
): Promise<{ rawApiToken: string; team: CreateTeamResponse["team"] }> {
  const data = await apiFetch(`${API_V1_TEAMS}/create`, CreateTeamResponseSchema, {
    method: "POST",
    body: { name },
    onSuccess: (d) => setAuthCookie(d.token),
  });
  return { rawApiToken: data.rawApiToken, team: data.team };
}

export async function joinTeam(code: string): Promise<{ team: JoinTeamResponse["team"] }> {
  const data = await apiFetch(`${API_V1_TEAMS}/join`, JoinTeamResponseSchema, {
    method: "POST",
    body: { code },
    onSuccess: (d) => setAuthCookie(d.token),
  });
  return { team: data.team };
}

export async function createInvite(): Promise<InviteResponse> {
  return apiFetch(`${API_V1_TEAMS}/invite`, InviteResponseSchema, {
    method: "POST",
  });
}

export async function listTokens(): Promise<ListTokensResponse> {
  return apiFetch(`${API_V1_TEAMS}/tokens`, ListTokensResponseSchema);
}

export async function createToken(label: string): Promise<CreateTokenResponse> {
  return apiFetch(`${API_V1_TEAMS}/tokens`, CreateTokenResponseSchema, {
    method: "POST",
    body: { label },
  });
}
