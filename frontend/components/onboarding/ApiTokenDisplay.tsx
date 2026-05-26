"use client";

import { CopyButton } from "@/components/ui/CopyButton";
import { PUBLIC_API_URL } from "@/lib/config";

interface ApiTokenDisplayProps {
  token: string;
}

function mcpConfig(token: string) {
  return JSON.stringify(
    {
      mcpServers: {
        canon: {
          url: `${PUBLIC_API_URL}/mcp`,
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2,
  );
}

const labelClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary";

export function ApiTokenDisplay({ token }: ApiTokenDisplayProps) {
  return (
    <div className="space-y-6">
      <p className={`${labelClass} text-canon-warning`}>
        Save this token — it won&apos;t be shown again
      </p>

      <div className="space-y-2">
        <p className={labelClass}>API Token</p>
        <div className="flex items-center border-b border-canon-border pb-2">
          <code className="flex-1 text-sm font-mono text-canon-text truncate">{token}</code>
          <CopyButton text={token} className="shrink-0 pl-3" />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className={labelClass}>MCP Config</p>
          <CopyButton text={mcpConfig(token)} />
        </div>
        <pre className="bg-canon-surface p-4 overflow-x-auto">
          <code className="text-xs font-mono text-canon-text">{mcpConfig(token)}</code>
        </pre>
      </div>
    </div>
  );
}
