"use server";

import { cookies } from "next/headers";
import {
  AuthResponseSchema,
  MeResponseSchema,
  type AuthResponse,
  type MeResponse,
} from "@/lib/schemas/auth";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: true,
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * 7,
};

async function handleErrorResponse(res: Response): Promise<never> {
  const err = await res.json().catch(() => null);
  throw new Error(
    (err as { detail?: string } | null)?.detail ??
      `Request failed: ${res.status}`
  );
}

export async function login(
  email: string,
  password: string
): Promise<AuthResponse["user"]> {
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
  const cookieStore = await cookies();
  cookieStore.set("canon_token", data.token, COOKIE_OPTIONS);

  return data.user;
}

export async function register(
  email: string,
  name: string,
  password: string
): Promise<AuthResponse["user"]> {
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
  const cookieStore = await cookies();
  cookieStore.set("canon_token", data.token, COOKIE_OPTIONS);

  return data.user;
}

export async function logout(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete("canon_token");
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
