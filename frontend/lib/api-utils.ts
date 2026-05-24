"use server";

import { cookies } from "next/headers";
import { COOKIE_NAME, COOKIE_OPTIONS } from "./constants";

async function logout(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
}

async function getAuthHeaders(
  includeContentType = false,
): Promise<Record<string, string>> {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
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
  cookieStore.set(COOKIE_NAME, token, COOKIE_OPTIONS);
}

export { getAuthHeaders, handleErrorResponse, logout, setAuthCookie };