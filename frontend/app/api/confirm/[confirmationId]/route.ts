import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/constants";
import { API_URL } from "@/lib/config";

export const runtime = "edge";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ confirmationId: string }> },
) {
  const { confirmationId } = await params;
  const token = request.cookies.get(COOKIE_NAME)?.value;

  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();

  const res = await fetch(`${API_URL}/api/v1/agent/confirm/${confirmationId}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const detail = await res.text();
    return NextResponse.json(
      { error: detail || "Confirmation failed" },
      { status: res.status },
    );
  }

  return NextResponse.json(await res.json());
}
