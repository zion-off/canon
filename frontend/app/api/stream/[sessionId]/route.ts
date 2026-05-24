import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const runtime = "edge";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("canon_token")?.value;

  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(request.url);
  const after = url.searchParams.get("after") ?? "0";

  const upstreamUrl = new URL(
    `/api/v1/sessions/${sessionId}/stream`,
    API_URL
  );
  upstreamUrl.searchParams.set("after", after);

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
