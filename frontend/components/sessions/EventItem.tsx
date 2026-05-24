"use client";

import type { AgentEvent } from "@/lib/schemas/sessions";
import { CollapsibleEvent } from "./CollapsibleEvent";
import { RunSeparator } from "./RunSeparator";
import { formatTimestamp } from "@/lib/date-utils";
import { isJsonContent } from "@/lib/text-utils";
import { EVENT_TYPE } from "@/lib/constants";

interface EventItemProps {
  event: AgentEvent;
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

    case EVENT_TYPE.TOOL_CALL_STARTED:
      return (
        <CollapsibleEvent
          icon="🔍"
          label={event.content?.split("\n")[0] ?? "Tool call"}
          content={event.content}
          timestamp={event.timestamp}
        />
      );

    case EVENT_TYPE.TOOL_CALL_COMPLETED:
      return (
        <CollapsibleEvent
          icon="✓"
          label={event.content?.split("\n")[0] ?? "Tool completed"}
          content={event.content}
          timestamp={event.timestamp}
        />
      );

    case EVENT_TYPE.REASONING_CHECKPOINT:
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
