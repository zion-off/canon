import { getCurrentUser } from "@/lib/actions/auth";
import { listTokens } from "@/lib/actions/teams";
import { redirect } from "next/navigation";
import { SettingsClient } from "@/components/settings/SettingsClient";

export default async function SettingsPage() {
  const user = await getCurrentUser();

  if (!user || user.role !== "owner") {
    redirect("/dashboard");
  }

  const tokens = await listTokens();

  return <SettingsClient initialTokens={tokens.tokens} />;
}
