"use client";

import { CopyButton } from "@/components/ui/CopyButton";
import { HighlightedCode } from "@/components/sessions/HighlightedCode";
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
      servers: {
        canon: {
          command: "uvx",
          args: ["canon-mcp-server"],
          env: {
            CANON_API_TOKEN: token,
            CANON_BACKEND_URL: PUBLIC_API_URL,
          },
        },
      },
    },
    null,
    2,
  );

  return (
    <div className="space-y-2">
      {label && <span className={labelClass}>{label}</span>}
      <div className="bg-canon-surface p-4 overflow-x-auto relative">
        <HighlightedCode code={config} lang="json" className="text-xs" />
        <div className="absolute top-2 right-2">
          <CopyButton text={config} />
        </div>
      </div>
    </div>
  );
}
