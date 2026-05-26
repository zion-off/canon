import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { COOKIE_NAME, API_V1_SESSIONS } from "@/lib/constants";
import { API_URL } from "@/lib/config";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;

  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const upstreamUrl = new URL(`${API_V1_SESSIONS}/stream`, API_URL);

  const upstream = await fetch(upstreamUrl.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!upstream.ok) {
    return NextResponse.json({ error: "Upstream error" }, { status: upstream.status });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
