import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { COOKIE_NAME } from "@/lib/constants";
import { API_URL, BACKEND_SSE_URL } from "@/lib/config";
import {
  StreamTokenResponseSchema,
  StreamUrlResponseSchema,
} from "@/lib/schemas/auth";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;

  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const streamTokenRes = await fetch(`${API_URL}/api/v1/sessions/stream/token`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!streamTokenRes.ok) {
    return NextResponse.json(
      { error: "Failed to issue stream token" },
      { status: streamTokenRes.status },
    );
  }

  const { token: streamToken } = StreamTokenResponseSchema.parse(
    await streamTokenRes.json(),
  );

  const backendUrl = new URL("api/v1/sessions/stream", BACKEND_SSE_URL);
  backendUrl.searchParams.set("token", streamToken);

  return NextResponse.json(
    StreamUrlResponseSchema.parse({ backendUrl: backendUrl.toString() }),
  );
}
