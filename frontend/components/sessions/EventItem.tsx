"use client";

import { useState } from "react";
import type { AgentEvent } from "@/lib/schemas/sessions";

interface EventItemProps {
  event: AgentEvent;
}

function isJsonContent(content: string): boolean {
  const trimmed = content.trim();
  return trimmed.startsWith("{") || trimmed.startsWith("[");
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function RunSeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="h-px flex-1 bg-slate-700/50" />
      <span className="text-xs text-slate-500">{label}</span>
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
      className="w-full rounded-md border border-white/[0.06] bg-[#0a0a18] px-4 py-3 text-left transition-colors hover:bg-[#10101f]"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-slate-300">
          <span>{icon}</span>
          <span className="font-medium">{label}</span>
          {!expanded && firstLine && (
            <span className="ml-2 truncate text-slate-500">{firstLine}</span>
          )}
        </div>
        {timestamp && (
          <span className="text-xs text-slate-500">
            {formatTimestamp(timestamp)}
          </span>
        )}
      </div>
      {expanded && content && (
        <div className="mt-3 border-t border-white/[0.06] pt-3">
          {isJsonContent(content) ? (
            <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs text-slate-400">
              {content}
            </pre>
          ) : (
            <p className="whitespace-pre-wrap text-sm text-slate-400">
              {content}
            </p>
          )}
        </div>
      )}
    </button>
  );
}

export function EventItem({ event }: EventItemProps) {
  switch (event.type) {
    case "run_started":
      return <RunSeparator label="Run started" />;

    case "run_completed":
      return <RunSeparator label="Run completed" />;

    case "subagent_invoked":
      return (
        <div className="py-1 pl-4">
          <span className="text-xs text-slate-500">
            ▶ {event.content ?? "Subagent"} started
          </span>
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
        <div className="rounded-md border-l-2 border-l-blue-500 bg-[#0c0c20] px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wide text-blue-400">
              Reasoning
            </span>
            {event.timestamp && (
              <span className="text-xs text-slate-500">
                {formatTimestamp(event.timestamp)}
              </span>
            )}
          </div>
          {event.content && (
            <p className="mt-2 whitespace-pre-wrap text-sm text-slate-200">
              {event.content}
            </p>
          )}
        </div>
      );

    case "final_response":
      return (
        <div className="rounded-md border-l-4 border-l-blue-500 bg-[#0d0d22] px-5 py-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wide text-blue-300">
              Final Response
            </span>
            {event.timestamp && (
              <span className="text-xs text-slate-500">
                {formatTimestamp(event.timestamp)}
              </span>
            )}
          </div>
          {event.content && (
            <div className="mt-3">
              {isJsonContent(event.content) ? (
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-sm text-slate-200">
                  {event.content}
                </pre>
              ) : (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
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
