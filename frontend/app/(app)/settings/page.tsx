import { getCurrentUser } from "@/lib/actions/auth";
import { listTokens } from "@/lib/actions/teams";
import { redirect } from "next/navigation";
import { ROUTE_DASHBOARD, ROLE_OWNER } from "@/lib/constants";
import { SettingsClient } from "@/components/settings/SettingsClient";

export default async function SettingsPage() {
  const user = await getCurrentUser();

  if (!user || user.role !== ROLE_OWNER) {
    redirect(ROUTE_DASHBOARD);
  }

  const tokens = await listTokens();

  return <SettingsClient initialTokens={tokens.tokens} />;
}
