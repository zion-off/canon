import { NextResponse, type NextRequest } from "next/server";
import { z } from "zod";
import { jwtVerify } from "jose";
import {
  COOKIE_NAME,
  PUBLIC_PATHS,
  ROUTE_DASHBOARD,
  ROUTE_LOGIN,
  ROUTE_ONBOARDING,
} from "@/lib/constants";
import { getJwtSecret } from "@/lib/config";

const jwtPayloadSchema = z.object({
  sub: z.string(),
  email: z.string(),
  name: z.string(),
  tenantId: z.string().nullable(),
  role: z.string().nullable(),
  iat: z.number(),
  exp: z.number(),
}).passthrough();

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next();
  }

  const token = request.cookies.get(COOKIE_NAME)?.value;

  if (!token) {
    return NextResponse.redirect(new URL(ROUTE_LOGIN, request.url));
  }

  try {
    const { payload } = await jwtVerify(token, getJwtSecret());
    const parseResult = jwtPayloadSchema.safeParse(payload);
    if (!parseResult.success) {
      return NextResponse.redirect(new URL(ROUTE_LOGIN, request.url));
    }
    const jwtPayload = parseResult.data;

    if (jwtPayload.tenantId === null && pathname !== ROUTE_ONBOARDING) {
      return NextResponse.redirect(new URL(ROUTE_ONBOARDING, request.url));
    }

    if (jwtPayload.tenantId !== null && pathname === ROUTE_ONBOARDING) {
      return NextResponse.redirect(new URL(ROUTE_DASHBOARD, request.url));
    }

    return NextResponse.next();
  } catch {
    return NextResponse.redirect(new URL(ROUTE_LOGIN, request.url));
  }
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
