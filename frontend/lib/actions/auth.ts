"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AuthResponseSchema, MeResponseSchema, type AuthResponse, type MeResponse } from "@/lib/schemas/auth";
import { API_URL, handleErrorResponse, logout, setAuthCookie } from "@/lib/api-utils";

export async function login(email: string, password: string): Promise<AuthResponse["user"]> {
  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    if (res.status === 401) {
      throw new Error("Invalid credentials");
    }
    await handleErrorResponse(res);
  }

  const data = AuthResponseSchema.parse(await res.json());
  await setAuthCookie(data.token);
  return data.user;
}

export async function register(email: string, name: string, password: string): Promise<AuthResponse["user"]> {
  const res = await fetch(`${API_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, password }),
  });

  if (!res.ok) {
    if (res.status === 409) {
      throw new Error("Email already registered");
    }
    await handleErrorResponse(res);
  }

  const data = AuthResponseSchema.parse(await res.json());
  await setAuthCookie(data.token);
  return data.user;
}

export { logout };

export async function handleLogout() {
  await logout();
  redirect("/login");
}

export async function getCurrentUser(): Promise<MeResponse | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("canon_token")?.value;

  if (!token) {
    return null;
  }

  const res = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    if (res.status === 401) {
      await logout();
      return null;
    }
    await handleErrorResponse(res);
  }

  return MeResponseSchema.parse(await res.json());
}
