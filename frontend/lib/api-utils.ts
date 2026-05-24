"use server";

import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 7,
};

async function logout(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete("canon_token");
}

async function getAuthHeaders(
  includeContentType = false,
): Promise<Record<string, string>> {
  const cookieStore = await cookies();
  const token = cookieStore.get("canon_token")?.value;
  if (!token) {
    throw new Error("Not authenticated");
  }
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (includeContentType) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function handleErrorResponse(res: Response): Promise<never> {
  if (res.status === 401) {
    await logout();
    throw new Error("Session expired");
  }
  const err = await res.json().catch(() => null);
  throw new Error(
    (err as { detail?: string } | null)?.detail ??
      `Request failed: ${res.status}`,
  );
}

async function setAuthCookie(token: string): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set("canon_token", token, COOKIE_OPTIONS);
}

export { API_URL, COOKIE_OPTIONS, getAuthHeaders, handleErrorResponse, logout, setAuthCookie };