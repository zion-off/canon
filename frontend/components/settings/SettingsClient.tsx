"use client";

import { useState } from "react";
import type { ApiToken } from "@/lib/schemas/teams";
import { InviteSection } from "./InviteSection";
import { TokenSection } from "./TokenSection";
import { formatShortDate } from "@/lib/date-utils";

interface SettingsClientProps {
  initialTokens: ApiToken[];
}

const labelClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em]";

export function SettingsClient({ initialTokens }: SettingsClientProps) {
  const [tokens, setTokens] = useState(initialTokens);
  const [tokenFormKey, setTokenFormKey] = useState(0);

  return (
    <div>
      <div className="h-10 flex items-center border-b border-canon-border -mx-5 px-5">
        <span className={`${labelClass} text-canon-text`}>Settings</span>
      </div>

      <div className="-mx-5">
        <div className="grid grid-cols-[1fr_2fr] border-b border-canon-border">
          <div className="px-5 py-6 border-r border-canon-border">
            <span className={`${labelClass} text-canon-text-secondary`}>Invite Members</span>
          </div>
          <div className="px-5 py-6">
            <InviteSection />
          </div>
        </div>

        <div className="grid grid-cols-[1fr_2fr] border-b border-canon-border">
          <div className="px-5 py-6 border-r border-canon-border">
            <span className={`${labelClass} text-canon-text-secondary`}>API Tokens</span>
          </div>
          <div className="px-5 py-6">
            <TokenSection
              key={tokenFormKey}
              onTokenAdded={(t) => {
                setTokens((prev) => [...prev, t]);
                setTokenFormKey((k) => k + 1);
              }}
            />
          </div>
        </div>

        {tokens.length > 0 && (
          <>
            {tokens.map((t) => (
              <div
                key={t.id || t.label}
                className="grid grid-cols-[1fr_2fr] border-b border-canon-border"
              >
                <div className="border-r border-canon-border" />
                <div className="px-5 py-3 flex items-baseline justify-between gap-4">
                  <span className="text-sm text-canon-text">{t.label}</span>
                  <span className="text-xs text-canon-text-secondary shrink-0">
                    Created {formatShortDate(t.createdAt)}
                    {t.lastUsedAt && ` · Last used ${formatShortDate(t.lastUsedAt)}`}
                  </span>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
