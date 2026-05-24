"use server";

import { z } from "zod";
import { API_URL } from "./constants";
import { getAuthHeaders, handleErrorResponse } from "./api-utils";

interface FetchOptions {
  json?: unknown;
  auth?: boolean;
  method?: string;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export async function apiFetch<T>(
  path: string,
  schema: z.ZodSchema<T>,
  options: FetchOptions = {},
): Promise<T> {
  const { json, auth = true, headers: extraHeaders, method, signal } = options;

  const headers: Record<string, string> = { ...(extraHeaders ?? {}) };

  if (auth) {
    const authHeaders = await getAuthHeaders(json !== undefined);
    Object.assign(headers, authHeaders);
  } else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const body = json !== undefined ? JSON.stringify(json) : undefined;

  const res = await fetch(`${API_URL}/${path}`, {
    method,
    headers,
    body,
    signal,
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return schema.parse(await res.json());
}
