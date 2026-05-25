export const API_BASE_URL = (process.env.API_URL ?? "http://localhost:8000") as string;

export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://YOUR_BACKEND_URL";

export const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET ?? "change-me-to-a-random-secret",
);
