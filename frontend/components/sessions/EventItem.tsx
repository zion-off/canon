"use client";

import { useState } from "react";
import type { AgentEvent } from "@/lib/schemas/sessions";
import { isJsonContent } from "@/lib/text-utils";
import { formatTimestamp } from "@/lib/date-utils";
import { EVENT_TYPE } from "@/lib/constants";

interface EventItemProps {
  event: AgentEvent;
}

function RunSeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="h-px flex-1 bg-slate-700/50" />
      <span className="text-xs text-canon-muted">{label}</span>
      <div className="h-px flex-1 bg-slate-700/50" />
    </div>
  );
}

function CollapsibleEvent({
  icon,
  label,
  content,
  timestamp,
}: {
  icon: string;
  label: string;
  content: string | null;
  timestamp: string | null;
}) {
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

export function EventItem({ event }: EventItemProps) {
  switch (event.type) {
    case EVENT_TYPE.RUN_STARTED:
      return <RunSeparator label="Run started" />;

    case EVENT_TYPE.RUN_COMPLETED:
      return <RunSeparator label="Run completed" />;

    case EVENT_TYPE.SUBAGENT_INVOKED:
      return (
        <div className="py-1 pl-4">
          <span className="text-xs text-canon-muted">▶ {event.content ?? "Subagent"} started</span>
        </div>
      );

    case "tool_call_started":
      return (
        <CollapsibleEvent
          icon="🔍"
          label={event.content?.split("\n")[0] ?? "Tool call"}
          content={event.content}
          timestamp={event.timestamp}
        />
      );

    case "tool_call_completed":
      return (
        <CollapsibleEvent
          icon="✓"
          label={event.content?.split("\n")[0] ?? "Tool completed"}
          content={event.content}
          timestamp={event.timestamp}
        />
      );

    case "reasoning_checkpoint":
      return (
        <div className="rounded-md border-l-2 border-l-canon-blue bg-[#0c0c20] px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wide text-blue-400">
              Reasoning
            </span>
            {event.timestamp && (
              <span className="text-xs text-canon-muted">{formatTimestamp(event.timestamp)}</span>
            )}
          </div>
          {event.content && (
            <p className="mt-2 whitespace-pre-wrap text-sm text-canon-text">{event.content}</p>
          )}
        </div>
      );

    case EVENT_TYPE.FINAL_RESPONSE:
      return (
        <div className="rounded-md border-l-4 border-l-canon-blue bg-[#0d0d22] px-5 py-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wide text-blue-300">
              Final Response
            </span>
            {event.timestamp && (
              <span className="text-xs text-canon-muted">{formatTimestamp(event.timestamp)}</span>
            )}
          </div>
          {event.content && (
            <div className="mt-3">
              {isJsonContent(event.content) ? (
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-sm text-canon-text">
                  {event.content}
                </pre>
              ) : (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-canon-text">
                  {event.content}
                </p>
              )}
            </div>
          )}
        </div>
      );

    default:
      return null;
  }
}
