"use client";

import { CopyButton } from "@/components/ui/CopyButton";
import { PUBLIC_API_URL } from "@/lib/config";

interface McpConfigDisplayProps {
  token?: string;
  label?: string;
}

const labelClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary";

export function McpConfigDisplay({
  token = "<YOUR_API_TOKEN>",
  label = "MCP Config",
}: McpConfigDisplayProps) {
  const config = JSON.stringify(
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

  return (
    <div className="space-y-2">
      {label && <span className={labelClass}>{label}</span>}
      <pre className="bg-canon-surface p-4 overflow-x-auto relative">
        <code className="text-xs font-mono text-canon-text whitespace-pre">{config}</code>
        <div className="absolute top-2 right-2">
          <CopyButton text={config} />
        </div>
      </pre>
    </div>
  );
}
