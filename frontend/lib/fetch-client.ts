"use server";

import { z } from "zod";
import { API_URL } from "./constants";
import { getAuthHeaders, handleErrorResponse } from "./api-utils";

interface FetchOptions extends Omit<RequestInit, "body"> {
  json?: unknown;
  auth?: boolean;
}

export async function apiFetch<T>(
  path: string,
  schema: z.ZodSchema<T>,
  options: FetchOptions = {},
): Promise<T> {
  const { json, auth = true, headers: extraHeaders, ...init } = options;

  const headers: Record<string, string> = { ...((extraHeaders as Record<string, string>) ?? {}) };

  if (auth) {
    const authHeaders = await getAuthHeaders(json !== undefined);
    Object.assign(headers, authHeaders);
  } else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}/${path}`, {
    ...init,
    headers,
    body: json !== undefined ? JSON.stringify(json) : init.body,
  });

  if (!res.ok) {
    await handleErrorResponse(res);
  }

  return schema.parse(await res.json());
}
