"use server";

import { cookies } from "next/headers";
import { z } from "zod";
import { API_URL } from "./config";
import { COOKIE_NAME, COOKIE_OPTIONS } from "./constants";

async function logout(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
}

async function getAuthHeaders(includeContentType = false): Promise<Record<string, string>> {
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
  if (err && typeof err === "object") {
    if (typeof err.detail === "string") {
      throw new Error(err.detail);
    }
    if (Array.isArray(err.detail)) {
      throw new Error(err.detail.map((d: { msg?: string }) => d.msg).join("; "));
    }
  }
  throw new Error(`Request failed: ${res.status}`);
}

async function setAuthCookie(token: string): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(COOKIE_NAME, token, COOKIE_OPTIONS);
}

interface ApiFetchOptions<T> {
  method?: string;
  body?: unknown;
  onSuccess?: (data: T) => Promise<void>;
}

async function apiFetch<T>(
  path: string,
  schema: z.ZodSchema<T>,
  options: ApiFetchOptions<T> = {},
): Promise<T> {
  const { method, body, onSuccess } = options;

  const authHeaders = await getAuthHeaders(body !== undefined);
  const res = await fetch(`${API_URL}/${path}`, {
    method,
    headers: authHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  const data = schema.parse(await res.json());

  if (onSuccess) {
    await onSuccess(data);
  }

  return data;
}

export { getAuthHeaders, handleErrorResponse, logout, setAuthCookie, apiFetch };
