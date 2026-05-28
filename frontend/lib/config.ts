export const API_URL = process.env.API_URL ?? "http://localhost:8000";

export const BACKEND_SSE_URL = process.env.BACKEND_SSE_URL ?? API_URL;

export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getJwtSecret(): Uint8Array {
  const secret = process.env.JWT_SECRET;
  if (!secret || secret === "change-me-to-a-random-secret") {
    throw new Error(
      "JWT_SECRET environment variable is not set — configure it to match your backend",
    );
  }
  return new TextEncoder().encode(secret);
}
