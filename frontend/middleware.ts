import { NextResponse, type NextRequest } from "next/server";
import { COOKIE_NAME, PUBLIC_PATHS, ROUTE_LOGIN, ROUTE_ONBOARDING } from "@/lib/constants";

interface JwtPayload {
  sub: string;
  email: string;
  name: string;
  tenantId: string | null;
  role: string | null;
  iat: number;
  exp: number;
}

function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const segments = token.split(".");
    if (segments.length !== 3) return null;
    const decoded = atob(segments[1].replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next();
  }

  const token = request.cookies.get(COOKIE_NAME)?.value;

  if (!token) {
    return NextResponse.redirect(new URL(ROUTE_LOGIN, request.url));
  }

  const payload = decodeJwtPayload(token);

  if (!payload || payload.exp * 1000 < Date.now()) {
    return NextResponse.redirect(new URL(ROUTE_LOGIN, request.url));
  }

  if (payload.tenantId === null && pathname !== ROUTE_ONBOARDING) {
    return NextResponse.redirect(new URL(ROUTE_ONBOARDING, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
