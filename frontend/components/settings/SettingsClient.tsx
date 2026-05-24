"use client";

import type { ApiToken } from "@/lib/schemas/teams";
import { InviteSection } from "./InviteSection";
import { TokenSection } from "./TokenSection";

interface SettingsClientProps {
  initialTokens: ApiToken[];
}

export function SettingsClient({ initialTokens }: SettingsClientProps) {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-syne text-3xl font-bold text-canon-text">Settings</h1>
        <p className="mt-1 text-sm text-canon-text-dim">
          Manage your team&apos;s invites and API tokens
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <InviteSection />
        <TokenSection initialTokens={initialTokens} />
      </div>
    </div>
  );
}
