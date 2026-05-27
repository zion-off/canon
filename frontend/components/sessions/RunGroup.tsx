"use client";

import type {
  IdentifiedEvent,
  DisplayItem,
  ToolCallPair,
  SubagentGroup,
} from "@/lib/schemas/sessions";
import { SubagentGroupItem } from "./SubagentGroupItem";
import { HighlightedCode } from "./HighlightedCode";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { formatDateTime, formatTimestamp } from "@/lib/date-utils";
import {
  EVENT_TYPE,
  DISPLAY_KIND,
  TOOL_NAME,
  SUBAGENT_TOOL_NAMES,
  TOOL_DISPLAY_NAMES,
  AGENT_DISPLAY_NAMES,
} from "@/lib/constants";

interface RunGroupProps {
  runIndex: number;
  events: IdentifiedEvent[];
  timestamp: string | null;
  invocationArgs: { request: string; context: string } | null;
}

type PairLocation =
  | { kind: "top-level"; idx: number }
  | { kind: "in-group"; groupIdx: number; pairIdx: number };

// Builds the display item list from a flat sequence of identified events:
// - subagent_invoked events become SubagentGroup containers
// - tool_call_started/completed pairs for subagent tools nest inside their group
// - outer AgentTool wrapper calls (tool_name matches a subagent name) are filtered out
// - emit_checkpoint tool pairs are filtered out (surfaced as ReasoningCheckpoint events)
// - all other events pass through unchanged
function pairToolCallEvents(events: IdentifiedEvent[]): DisplayItem[] {
  const result: DisplayItem[] = [];
  const pendingGroups = new Map<string, number>(); // agentInvocationId → result idx
  const pendingPairs = new Map<string, PairLocation>(); // invocationId → location

  for (const event of events) {
    if (event.type === EVENT_TYPE.SUBAGENT_INVOKED) {
      const group: SubagentGroup = {
        kind: DISPLAY_KIND.SUBAGENT_GROUP,
        stableId: event.stableId,
        agentInvocationId: event.payload.agent_invocation_id,
        agentName: event.payload.agent_name,
        timestamp: event.timestamp,
        toolPairs: [],
      };
      pendingGroups.set(event.payload.agent_invocation_id, result.length);
      result.push(group);
    } else if (event.type === EVENT_TYPE.TOOL_CALL_STARTED) {
      if (
        event.payload.tool_name === TOOL_NAME.EMIT_CHECKPOINT ||
        SUBAGENT_TOOL_NAMES.has(event.payload.tool_name)
      )
        continue;

      const pair: ToolCallPair = {
        kind: DISPLAY_KIND.TOOL_CALL_PAIR,
        stableId: event.stableId,
        invocationId: event.payload.invocation_id,
        started: event,
        completed: null,
      };

      const agentInvId = event.payload.agent_invocation_id;
      const groupIdx = agentInvId != null ? pendingGroups.get(agentInvId) : undefined;

      if (groupIdx !== undefined) {
        const group = result[groupIdx] as SubagentGroup;
        const pairIdx = group.toolPairs.length;
        group.toolPairs.push(pair);
        pendingPairs.set(event.payload.invocation_id, { kind: "in-group", groupIdx, pairIdx });
      } else {
        pendingPairs.set(event.payload.invocation_id, { kind: "top-level", idx: result.length });
        result.push(pair);
      }
    } else if (event.type === EVENT_TYPE.TOOL_CALL_COMPLETED) {
      if (
        event.payload.tool_name === TOOL_NAME.EMIT_CHECKPOINT ||
        SUBAGENT_TOOL_NAMES.has(event.payload.tool_name)
      )
        continue;

      const location = pendingPairs.get(event.payload.invocation_id);
      if (location === undefined) continue;

      if (location.kind === "top-level") {
        const existing = result[location.idx] as ToolCallPair;
        result[location.idx] = { ...existing, completed: event };
      } else {
        const group = result[location.groupIdx] as SubagentGroup;
        group.toolPairs[location.pairIdx] = {
          ...group.toolPairs[location.pairIdx],
          completed: event,
        };
      }
      pendingPairs.delete(event.payload.invocation_id);
    } else {
      result.push(event);
    }
  }

  return result;
}

const STATUS_DISPLAY: Record<string, string> = { ok: "Done", error: "Failed" };

// Shimmer class reused from ToolCallTimeline's active connector line
const SHIMMER_LINE =
  "bg-[linear-gradient(to_bottom,_rgb(48,48,48)_0%,_rgb(48,48,48)_25%,_rgba(255,255,255,0.6)_50%,_rgb(48,48,48)_75%,_rgb(48,48,48)_100%)] bg-[length:100%_200%] [animation:shimmer_1.5s_linear_infinite]";

interface TimelineSlotProps {
  dot: string;
  dotPt?: string;
  dotPulse?: boolean;
  isLast: boolean;
  lineActive: boolean;
  children: React.ReactNode;
}

function TimelineSlot({
  dot,
  dotPt = "pt-1.5",
  dotPulse = false,
  isLast,
  lineActive,
  children,
}: TimelineSlotProps) {
  return (
    <div className="flex gap-3">
      <div className={`flex flex-col items-center ${dotPt}`}>
        <div
          className={`w-2 h-2 rounded-full shrink-0 ${dot}${dotPulse ? " animate-pulse" : ""}`}
        />
        {!isLast && (
          <div className={`w-px flex-1 mt-1 ${lineActive ? SHIMMER_LINE : "bg-canon-border"}`} />
        )}
      </div>
      <div className={`min-w-0 flex-1 ${isLast ? "pb-1" : "pb-4"}`}>{children}</div>
    </div>
  );
}

function ToolCallContent({ pair }: { pair: ToolCallPair }) {
  const { started, completed } = pair;
  const toolName = TOOL_DISPLAY_NAMES[started.payload.tool_name] ?? started.payload.tool_name;
  const authorName = started.author
    ? (AGENT_DISPLAY_NAMES[started.author] ?? started.author)
    : null;
  const isPending = completed === null;
  const isSuccess = completed?.payload.status === "ok";

  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="text-sm font-medium text-canon-text">{toolName}</span>
          {authorName && (
            <span className="text-xs text-canon-text-disabled font-condensed">{authorName}</span>
          )}
        </div>
        {started.timestamp && (
          <span suppressHydrationWarning className="shrink-0 text-xs text-canon-text-disabled">
            {formatTimestamp(started.timestamp)}
          </span>
        )}
      </div>
      {Object.keys(started.payload.args).length > 0 && (
        <HighlightedCode
          code={JSON.stringify(started.payload.args, null, 2)}
          lang="json"
          className="mt-1 text-xs"
        />
      )}
      <div
        className={`mt-2 flex items-baseline justify-between gap-4 ${isPending ? "items-center" : ""}`}
      >
        <span
          className={`text-xs font-condensed font-bold uppercase tracking-wider ${
            isPending
              ? "text-canon-warning italic normal-case"
              : isSuccess
                ? "text-canon-success"
                : "text-canon-error"
          }`}
        >
          {isPending
            ? "running…"
            : (STATUS_DISPLAY[completed.payload.status] ?? completed.payload.status)}
        </span>
        {completed?.timestamp && (
          <span suppressHydrationWarning className="shrink-0 text-xs text-canon-text-disabled">
            {formatTimestamp(completed.timestamp)}
          </span>
        )}
      </div>
      {completed?.payload.result != null && (
        <HighlightedCode
          code={
            typeof completed.payload.result === "string"
              ? completed.payload.result
              : JSON.stringify(completed.payload.result, null, 2)
          }
          lang={typeof completed.payload.result === "string" ? "txt" : "json"}
          className="mt-1 text-xs"
        />
      )}
    </div>
  );
}

export function RunGroup({ runIndex, events, timestamp, invocationArgs }: RunGroupProps) {
  const visibleEvents = events.filter(
    (e) => e.type !== EVENT_TYPE.RUN_STARTED && e.type !== EVENT_TYPE.RUN_COMPLETED,
  );
  const displayItems = pairToolCallEvents(visibleEvents);
  const isRunActive = !events.some((e) => e.type === EVENT_TYPE.RUN_COMPLETED);

  const harnessOffset = invocationArgs != null ? 1 : 0;
  const totalSlots = harnessOffset + displayItems.length;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 pb-1 pt-4">
        <span className="text-sm font-medium text-canon-text">Run {runIndex}</span>
        {timestamp && (
          <>
            <span className="text-canon-text-secondary">·</span>
            <span suppressHydrationWarning className="text-xs text-canon-text-secondary">
              {formatDateTime(timestamp)}
            </span>
          </>
        )}
      </div>

      <div>
        {invocationArgs && (
          <TimelineSlot
            dot="bg-canon-accent"
            dotPt="pt-1"
            isLast={totalSlots === 1}
            lineActive={isRunActive}
          >
            <div className="leading-4">
              <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent">
                Harness Request
              </span>
              <HighlightedCode
                code={JSON.stringify(invocationArgs, null, 2)}
                lang="json"
                className="mt-1 text-xs"
              />
            </div>
          </TimelineSlot>
        )}

        {displayItems.map((item, i) => {
          const isLast = harnessOffset + i === totalSlots - 1;

          if (item.kind === DISPLAY_KIND.TOOL_CALL_PAIR) {
            const isPending = item.completed === null;
            const isSuccess = item.completed?.payload.status === "ok";
            const dot = isPending
              ? "bg-canon-warning"
              : isSuccess
                ? "bg-canon-success"
                : "bg-canon-error";
            return (
              <TimelineSlot
                key={item.stableId}
                dot={dot}
                dotPulse={isPending}
                isLast={isLast}
                lineActive={isRunActive && !isPending}
              >
                <ToolCallContent pair={item} />
              </TimelineSlot>
            );
          }

          if (item.kind === DISPLAY_KIND.SUBAGENT_GROUP) {
            const hasActivePairs = item.toolPairs.some((p) => p.completed === null);
            return (
              <TimelineSlot
                key={item.stableId}
                dot="bg-canon-text-secondary"
                dotPt="pt-1"
                isLast={isLast}
                lineActive={isRunActive && !hasActivePairs}
              >
                <SubagentGroupItem group={item} />
              </TimelineSlot>
            );
          }

          if (item.type === EVENT_TYPE.REASONING_CHECKPOINT) {
            return (
              <TimelineSlot
                key={item.stableId}
                dot="bg-canon-accent"
                isLast={isLast}
                lineActive={isRunActive}
              >
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-canon-text">
                  {item.payload.message}
                </p>
              </TimelineSlot>
            );
          }

          if (item.type === EVENT_TYPE.FINAL_RESPONSE) {
            return (
              <TimelineSlot
                key={item.stableId}
                dot="bg-canon-accent"
                dotPt="pt-1"
                isLast={isLast}
                lineActive={isRunActive}
              >
                <div>
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="text-sm font-medium text-canon-text">Final Response</span>
                    {item.timestamp && (
                      <span
                        suppressHydrationWarning
                        className="shrink-0 text-xs text-canon-text-disabled"
                      >
                        {formatTimestamp(item.timestamp)}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 px-1">
                    <MarkdownRenderer>{item.payload.text}</MarkdownRenderer>
                  </div>
                </div>
              </TimelineSlot>
            );
          }

          return null;
        })}
      </div>
    </div>
  );
}
