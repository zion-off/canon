import { NextResponse, type NextRequest } from "next/server";
import { jwtVerify } from "jose";
import { COOKIE_NAME, PUBLIC_PATHS, ROUTE_LOGIN, ROUTE_ONBOARDING } from "@/lib/constants";
import { getJwtSecret } from "@/lib/config";

interface JwtPayload {
  sub: string;
  email: string;
  name: string;
  tenantId: string | null;
  role: string | null;
  iat: number;
  exp: number;
}

export async function middleware(request: NextRequest) {
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
    const jwtPayload = payload as unknown as JwtPayload;

    if (jwtPayload.tenantId === null && pathname !== ROUTE_ONBOARDING) {
      return NextResponse.redirect(new URL(ROUTE_ONBOARDING, request.url));
    }

    return NextResponse.next();
  } catch {
    return NextResponse.redirect(new URL(ROUTE_LOGIN, request.url));
  }
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
