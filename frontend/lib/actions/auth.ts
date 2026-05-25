"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AuthResponseSchema, MeResponseSchema } from "@/lib/schemas/auth";
import type { AuthResponse, MeResponse } from "@/lib/schemas/auth";
import { COOKIE_NAME, API_V1_AUTH, ROUTE_LOGIN } from "@/lib/constants";
import { API_URL } from "@/lib/config";
import { handleErrorResponse, logout, setAuthCookie } from "@/lib/api-utils";

export async function login(email: string, password: string): Promise<AuthResponse["user"]> {
  const res = await fetch(`${API_URL}/${API_V1_AUTH}/login`, {
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

export async function register(
  email: string,
  name: string,
  password: string,
): Promise<AuthResponse["user"]> {
  const res = await fetch(`${API_URL}/${API_V1_AUTH}/register`, {
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
    if (res.status === 401) {
      await logout();
      return null;
    }
    await handleErrorResponse(res);
  }

  return MeResponseSchema.parse(await res.json());
}
