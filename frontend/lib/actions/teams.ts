"use server";

import { cookies } from "next/headers";
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
import { logout } from "@/lib/actions/auth";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 7,
};

async function getAuthHeaders(): Promise<Record<string, string>> {
  const cookieStore = await cookies();
  const token = cookieStore.get("canon_token")?.value;
  if (!token) {
    throw new Error("Not authenticated");
  }
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
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

export async function createTeam(
  name: string
): Promise<{ rawApiToken: string; team: CreateTeamResponse["team"] }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/teams/create`, {
    method: "POST",
    headers,
    body: JSON.stringify({ name }),
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  const data = CreateTeamResponseSchema.parse(await res.json());
  const cookieStore = await cookies();
  cookieStore.set("canon_token", data.token, COOKIE_OPTIONS);

  return { rawApiToken: data.rawApiToken, team: data.team };
}

export async function joinTeam(
  code: string
): Promise<{ team: JoinTeamResponse["team"] }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/teams/join`, {
    method: "POST",
    headers,
    body: JSON.stringify({ code }),
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  const data = JoinTeamResponseSchema.parse(await res.json());
  const cookieStore = await cookies();
  cookieStore.set("canon_token", data.token, COOKIE_OPTIONS);

  return { team: data.team };
}

export async function createInvite(): Promise<InviteResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/teams/invite`, {
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
  const res = await fetch(`${API_URL}/api/v1/teams/tokens`, {
    headers,
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return ListTokensResponseSchema.parse(await res.json());
}

export async function createToken(label: string): Promise<CreateTokenResponse> {
  const headers = await getAuthHeaders();
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
