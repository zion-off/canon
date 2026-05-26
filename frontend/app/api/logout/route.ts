import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { COOKIE_NAME, ROUTE_LOGIN } from "@/lib/constants";

export async function GET() {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
  redirect(ROUTE_LOGIN);
}

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
  redirect(ROUTE_LOGIN);
}
