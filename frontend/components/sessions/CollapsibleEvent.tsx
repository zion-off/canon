"use client";

import { useState } from "react";
import { isJsonContent } from "@/lib/text-utils";
import { formatTimestamp } from "@/lib/date-utils";

interface CollapsibleEventProps {
  icon: string;
  label: string;
  content: string | null;
  timestamp: string | null;
}

export function CollapsibleEvent({ icon, label, content, timestamp }: CollapsibleEventProps) {
  const [expanded, setExpanded] = useState(false);
  const firstLine = content?.split("\n")[0] ?? "";

  return (
    <button
      type="button"
      onClick={() => setExpanded((prev) => !prev)}
      className="w-full rounded-md border border-canon-border bg-[#0a0a18] px-4 py-3 text-left transition-colors hover:bg-[#10101f]"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-canon-text">
          <span>{icon}</span>
          <span className="font-medium">{label}</span>
          {!expanded && firstLine && (
            <span className="ml-2 truncate text-canon-muted">{firstLine}</span>
          )}
        </div>
        {timestamp && (
          <span className="text-xs text-canon-muted">{formatTimestamp(timestamp)}</span>
        )}
      </div>
      {expanded && content && (
        <div className="mt-3 border-t border-canon-border pt-3">
          {isJsonContent(content) ? (
            <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs text-canon-text-dim">
              {content}
            </pre>
          ) : (
            <p className="whitespace-pre-wrap text-sm text-canon-text-dim">{content}</p>
          )}
        </div>
      )}
    </button>
  );
}
