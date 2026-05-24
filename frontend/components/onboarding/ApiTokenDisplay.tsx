"use client";

import { useState } from "react";

interface ApiTokenDisplayProps {
  token: string;
}

export function ApiTokenDisplay({ token }: ApiTokenDisplayProps) {
  const [copied, setCopied] = useState(false);

  async function copyToClipboard() {
    await navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const cursorConfig = JSON.stringify(
    {
      mcpServers: {
        canon: {
          url: "https://YOUR_BACKEND_URL/mcp",
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2
  );

  const claudeConfig = JSON.stringify(
    {
      mcpServers: {
        canon: {
          url: "https://YOUR_BACKEND_URL/mcp",
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2
  );

  return (
    <div className="space-y-5">
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3">
        <p className="text-sm font-medium text-amber-400">
          Save this token — it won&apos;t be shown again
        </p>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wide">
          API Token
        </label>
        <div className="relative">
          <pre className="bg-[#161625] border border-white/[0.08] rounded-lg p-4 overflow-x-auto">
            <code className="text-sm font-mono text-slate-200 break-all">
              {token}
            </code>
          </pre>
          <button
            type="button"
            onClick={copyToClipboard}
            className="absolute top-2 right-2 px-2.5 py-1 text-xs font-medium rounded-md bg-white/[0.06] border border-white/[0.08] text-slate-300 hover:bg-white/[0.1] transition-colors"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wide">
          MCP Configuration — Cursor
        </label>
        <pre className="bg-[#161625] border border-white/[0.08] rounded-lg p-4 overflow-x-auto">
          <code className="text-xs font-mono text-slate-300">
            {`// .cursor/mcp.json\n${cursorConfig}`}
          </code>
        </pre>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wide">
          MCP Configuration — Claude Code
        </label>
        <pre className="bg-[#161625] border border-white/[0.08] rounded-lg p-4 overflow-x-auto">
          <code className="text-xs font-mono text-slate-300">
            {`// claude_desktop_config.json\n${claudeConfig}`}
          </code>
        </pre>
      </div>
    </div>
  );
}
