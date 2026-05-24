import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = new Set(["/", "/login", "/register"]);

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
    const payload = segments[1];
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  const token = request.cookies.get("canon_token")?.value;

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  const payload = decodeJwtPayload(token);

  if (!payload || payload.exp * 1000 < Date.now()) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  if (payload.tenantId === null && pathname !== "/onboarding") {
    const onboardingUrl = new URL("/onboarding", request.url);
    return NextResponse.redirect(onboardingUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
