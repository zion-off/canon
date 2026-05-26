import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/actions/auth";
import { ROUTE_DASHBOARD } from "@/lib/constants";
import LandingPage from "@/components/landing/LandingPage";

export default async function Home() {
  const user = await getCurrentUser();

  if (user) {
    redirect(ROUTE_DASHBOARD);
  }

  return <LandingPage />;
}
