"use client";

import { useState } from "react";
import { isJsonContent } from "@/lib/text-utils";
import { formatTimestamp } from "@/lib/date-utils";

interface CollapsibleEventProps {
  label: string;
  content: string | null;
  timestamp: string | null;
}

export function CollapsibleEvent({ label, content, timestamp }: CollapsibleEventProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-canon-border">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full flex items-center justify-between gap-3 py-2 text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="shrink-0 font-condensed font-bold text-xs text-canon-text-disabled">
            {expanded ? "▲" : "▼"}
          </span>
          <span className="text-sm text-canon-text-secondary truncate">{label}</span>
        </div>
        {timestamp && (
          <span suppressHydrationWarning className="shrink-0 text-xs text-canon-text-disabled">
            {formatTimestamp(timestamp)}
          </span>
        )}
      </button>

      {expanded && content && (
        <div className="pb-3">
          {isJsonContent(content) ? (
            <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs text-canon-text-secondary">
              {content}
            </pre>
          ) : (
            <p className="whitespace-pre-wrap text-sm text-canon-text-secondary">{content}</p>
          )}
        </div>
      )}
    </div>
  );
}
