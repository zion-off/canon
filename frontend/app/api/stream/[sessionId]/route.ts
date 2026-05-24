import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

export const runtime = "edge";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params;
  // Edge Runtime: read cookie from the request directly (no next/headers)
  const token = request.cookies.get("canon_token")?.value;

  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(request.url);
  const after = url.searchParams.get("after") ?? "0";

  const upstreamUrl = new URL(
    `/api/v1/sessions/${sessionId}/stream`,
    API_URL
  );
  upstreamUrl.searchParams.set("last_event_id", after);

  const upstream = await fetch(upstreamUrl.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!upstream.ok) {
    return NextResponse.json(
      { error: "Upstream error" },
      { status: upstream.status }
    );
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
