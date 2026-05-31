"use client";

import { useMemo } from "react";
import { motion } from "motion/react";
import type {
  IdentifiedEvent,
  ConfirmationRequestedEvent,
  ConfirmationReceivedEvent,
} from "@/lib/schemas/sessions";
import { EVENT_TYPE, TOOL_CALL_STATUS } from "@/lib/constants";
import { PHASE_LABELS, PHASE_ITEM_KIND } from "./types";
import type { CognitivePhase } from "./types";
import { buildPhaseGroups } from "./phase-utils";
import { IntentHeader } from "./IntentHeader";
import { ThoughtCard } from "./ThoughtCard";
import { ToolCallSentenceCard } from "./ToolCallSentenceCard";
import { SubagentGroupCard } from "./SubagentGroupCard";
import { FinalResponseCard } from "./FinalResponseCard";
import { ConfirmationCard } from "./ConfirmationCard";
import { MemoryBornGraph } from "./MemoryBornGraph";
import type { CanonizeNodeArgs, CanonizeNodeResult } from "./types";

const STATIC_SPINE = "bg-canon-border";

interface RunGroupProps {
  events: IdentifiedEvent[];
  isLive: boolean;
}

export function RunGroup({ events, isLive }: RunGroupProps) {
  const runStarted = events.find((e) => e.type === EVENT_TYPE.RUN_STARTED);
  const invocationArgs =
    runStarted?.type === EVENT_TYPE.RUN_STARTED
      ? { request: runStarted.payload.request, context: runStarted.payload.context }
      : null;

  const confirmationResolutions = useMemo(() => {
    const map = new Map<string, ConfirmationReceivedEvent>();
    const received = events.filter((e) => e.type === EVENT_TYPE.CONFIRMATION_RECEIVED);
    if (received.length > 0) {
      const lastReceived = received[received.length - 1] as ConfirmationReceivedEvent;
      const requested = events.filter((e) => e.type === EVENT_TYPE.CONFIRMATION_REQUESTED);
      if (requested.length > 0) {
        const lastRequested = requested[requested.length - 1] as ConfirmationRequestedEvent;
        map.set(lastRequested.payload.confirmationId, lastReceived);
      }
    }
    return map;
  }, [events]);

  const phaseGroups = useMemo(() => buildPhaseGroups(events), [events]);

  let itemIndex = 0;

  return (
    <div className="space-y-0">
      {invocationArgs && (
        <IntentHeader
          request={invocationArgs.request}
          context={invocationArgs.context}
          isLive={isLive && phaseGroups.length === 0}
        />
      )}

      {phaseGroups.map((group, gi) => {
        const isActiveGroup = isLive && gi === phaseGroups.length - 1;
        const hasSpineBelow = gi < phaseGroups.length - 1 || isLive;

        return (
          <div key={`${group.phase}-${gi}`} className="flex gap-3">
            <div className="flex flex-col items-center w-3 shrink-0">
              <div className="h-5 shrink-0 flex items-center justify-center">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    isActiveGroup ? "bg-canon-accent animate-pulse" : "bg-canon-text-disabled"
                  }`}
                />
              </div>
              {hasSpineBelow && <div className={`w-px flex-1 min-h-2 ${STATIC_SPINE}`} />}
            </div>

            {/* Right column: phase header + items */}
            <div className="flex-1 min-w-0 pb-3">
              <PhaseLabel phase={group.phase} index={gi} />
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const idx = itemIndex++;
                  switch (item.kind) {
                    case PHASE_ITEM_KIND.THOUGHT:
                      return (
                        <ThoughtCard
                          key={item.event.stableId}
                          message={item.event.payload.message}
                          index={idx}
                        />
                      );
                    case PHASE_ITEM_KIND.TOOL_PAIR:
                      return (
                        <ToolCallSentenceCard
                          key={item.pair.stableId}
                          pair={item.pair}
                          index={idx}
                        />
                      );
                    case PHASE_ITEM_KIND.SUBAGENT_GROUP: {
                      const subagentActive =
                        isActiveGroup && !item.group.toolPairs.every((p) => p.completed !== null);
                      return (
                        <SubagentGroupCard
                          key={item.group.stableId}
                          group={item.group}
                          index={idx}
                          isActive={subagentActive}
                        />
                      );
                    }
                    case PHASE_ITEM_KIND.FINAL_RESPONSE:
                      return (
                        <FinalResponseCard
                          key={item.event.stableId}
                          text={item.event.payload.text}
                          index={idx}
                        />
                      );
                    case PHASE_ITEM_KIND.CONFIRMATION_REQUESTED: {
                      const resolution = confirmationResolutions.get(
                        item.event.payload.confirmationId,
                      );
                      return (
                        <ConfirmationCard
                          key={item.event.stableId}
                          event={item.event}
                          resolution={resolution}
                          index={idx}
                        />
                      );
                    }
                    case PHASE_ITEM_KIND.CONFIRMATION_RECEIVED:
                      return null;
                    case PHASE_ITEM_KIND.CANONIZE_PAIR: {
                      const args = item.pair.started.payload.args as CanonizeNodeArgs;
                      const result = item.pair.completed?.payload.result as
                        | CanonizeNodeResult
                        | undefined;
                      if (item.pair.completed?.payload.status === TOOL_CALL_STATUS.OK && result) {
                        return (
                          <MemoryBornGraph
                            key={item.pair.stableId}
                            args={args}
                            result={result}
                            index={idx}
                          />
                        );
                      }
                      return (
                        <ToolCallSentenceCard
                          key={item.pair.stableId}
                          pair={item.pair}
                          index={idx}
                        />
                      );
                    }
                    default:
                      return null;
                  }
                })}
              </div>
            </div>
          </div>
        );
      })}

      {isLive && phaseGroups.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-2 pt-1 pl-6"
        >
          <span className="inline-block h-1 w-1 rounded-full bg-canon-success animate-pulse" />
          <span className="text-xs text-canon-text-secondary italic">Processing…</span>
        </motion.div>
      )}
    </div>
  );
}

function PhaseLabel({ phase, index }: { phase: CognitivePhase; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: index * 0.05 }}
      className="flex items-center gap-2 pt-1 pb-2"
    >
      <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
        {PHASE_LABELS[phase]}
      </span>
    </motion.div>
  );
}
