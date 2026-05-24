"use client";

import { CopyButton } from "@/components/ui/CopyButton";

interface ApiTokenDisplayProps {
  token: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://YOUR_BACKEND_URL";

export function ApiTokenDisplay({ token }: ApiTokenDisplayProps) {
  const mcpUrl = `${API_BASE_URL}/mcp`;

  const cursorConfig = JSON.stringify(
    {
      mcpServers: {
        canon: {
          url: mcpUrl,
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2,
  );

  const claudeConfig = JSON.stringify(
    {
      mcpServers: {
        canon: {
          url: mcpUrl,
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2,
  );

  return (
    <div className="space-y-5">
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3">
        <p className="text-sm font-medium text-amber-400">
          Save this token — it won&apos;t be shown again
        </p>
      </div>

      <div>
        <p className="text-xs font-medium text-canon-text-dim mb-2 uppercase tracking-wide">
          API Token
        </p>
        <div className="relative">
          <pre className="bg-canon-surface-2 border border-canon-border rounded-lg p-4 overflow-x-auto">
            <code className="text-sm font-mono text-canon-text break-all">{token}</code>
          </pre>
          <CopyButton text={token} className="absolute top-2 right-2" />
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-canon-text-dim mb-2 uppercase tracking-wide">
          MCP Configuration — Cursor
        </p>
        <pre className="bg-canon-surface-2 border border-canon-border rounded-lg p-4 overflow-x-auto">
          <code className="text-xs font-mono text-canon-text">
            {`// .cursor/mcp.json\n${cursorConfig}`}
          </code>
        </pre>
      </div>

      <div>
        <p className="text-xs font-medium text-canon-text-dim mb-2 uppercase tracking-wide">
          MCP Configuration — Claude Code
        </p>
        <pre className="rounded-lg border border-canon-border bg-canon-surface-2 p-4 overflow-x-auto">
          <code className="text-xs font-mono text-canon-text">
            {`// claude_desktop_config.json\n${claudeConfig}`}
          </code>
        </pre>
      </div>

      <div>
        <p className="text-xs font-medium text-canon-text-dim mb-2 uppercase tracking-wide">
          MCP Configuration — Gemini CLI
        </p>
        <pre className="rounded-lg border border-canon-border bg-canon-surface-2 p-4 overflow-x-auto">
          <code className="text-xs font-mono text-canon-text">
            {`// .gemini/settings.json\n${JSON.stringify(
              {
                mcpServers: {
                  canon: {
                    url: mcpUrl,
                    headers: { Authorization: `Bearer ${token}` },
                  },
                },
              },
              null,
              2,
            )}`}
          </code>
        </pre>
      </div>
    </div>
  );
}
