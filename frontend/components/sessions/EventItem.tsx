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
          <span className="text-xs text-canon-text-secondary">
            ▶ {event.payload.agent_name}
          </span>
        </div>
      );

    case EVENT_TYPE.TOOL_CALL_STARTED:
      return (
        <CollapsibleEvent
          label={event.payload.tool_name}
          content={JSON.stringify(event.payload.args, null, 2)}
          timestamp={event.timestamp}
        />
      );

    case EVENT_TYPE.TOOL_CALL_COMPLETED:
      return (
        <CollapsibleEvent
          label={`${event.payload.tool_name} → ${event.payload.status}`}
          content={JSON.stringify(event.payload.result, null, 2)}
          timestamp={event.timestamp}
        />
      );

    case EVENT_TYPE.REASONING_CHECKPOINT:
      return (
        <div className="border-l-2 border-l-canon-accent bg-canon-surface px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent">
              Reasoning
            </span>
            {event.timestamp && (
              <span suppressHydrationWarning className="text-xs text-canon-text-secondary">
                {formatTimestamp(event.timestamp)}
              </span>
            )}
          </div>
          <p className="mt-2 whitespace-pre-wrap text-sm text-canon-text">
            {event.payload.message}
          </p>
        </div>
      );

    case EVENT_TYPE.FINAL_RESPONSE:
      return (
        <div className="border-l-4 border-l-canon-accent bg-canon-surface-raised px-5 py-4">
          <div className="flex items-center justify-between">
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent">
              Final Response
            </span>
            {event.timestamp && (
              <span suppressHydrationWarning className="text-xs text-canon-text-secondary">
                {formatTimestamp(event.timestamp)}
              </span>
            )}
          </div>
          <div className="mt-3">
            {isJsonContent(event.payload.text) ? (
              <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-sm text-canon-text">
                {event.payload.text}
              </pre>
            ) : (
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-canon-text">
                {event.payload.text}
              </p>
            )}
          </div>
        </div>
      );

    default:
      return null;
  }
}
