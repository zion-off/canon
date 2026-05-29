"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AuthResponseSchema, MeResponseSchema } from "@/lib/schemas/auth";
import type { AuthResponse, MeResponse } from "@/lib/schemas/auth";
import { COOKIE_NAME, API_V1_AUTH, ROUTE_LOGIN } from "@/lib/constants";
import { API_URL } from "@/lib/config";
import { logout, setAuthCookie } from "@/lib/api-utils";

export type AuthActionResult =
  | { success: true; user: AuthResponse["user"] }
  | { success: false; error: string };

export async function login(email: string, password: string): Promise<AuthActionResult> {
  const res = await fetch(`${API_URL}/${API_V1_AUTH}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    if (res.status === 401) {
      const err = await res.json().catch(() => null);
      return { success: false, error: err?.detail ?? "Invalid credentials" };
    }
    const body = await res.json().catch(() => null);
    const detail =
      body && typeof body.detail === "string" ? body.detail : `Request failed: ${res.status}`;
    return { success: false, error: detail };
  }

  const data = AuthResponseSchema.parse(await res.json());
  await setAuthCookie(data.token);
  return { success: true, user: data.user };
}

export async function register(
  email: string,
  name: string,
  password: string,
): Promise<AuthActionResult> {
  const res = await fetch(`${API_URL}/${API_V1_AUTH}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, password }),
  });

  if (!res.ok) {
    if (res.status === 409) {
      return { success: false, error: "Email already registered" };
    }
    const body = await res.json().catch(() => null);
    const detail =
      body && typeof body.detail === "string" ? body.detail : `Request failed: ${res.status}`;
    return { success: false, error: detail };
  }

  const data = AuthResponseSchema.parse(await res.json());
  await setAuthCookie(data.token);
  return { success: true, user: data.user };
}

export { logout };

export async function handleLogout() {
  await logout();
  redirect(ROUTE_LOGIN);
}

export async function getCurrentUser(): Promise<MeResponse | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;

  if (!token) {
    return null;
  }

  const res = await fetch(`${API_URL}/${API_V1_AUTH}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    return null;
  }

  return MeResponseSchema.parse(await res.json());
}
