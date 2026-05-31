"use client";

import { useMemo } from "react";
import { motion } from "motion/react";
import { z } from "zod";
import type { IdentifiedEvent, ConfirmationReceivedEvent } from "@/lib/schemas/sessions";
import {
  ConfirmationReceivedEventSchema,
  ReasoningCheckpointPayloadSchema,
  FinalResponsePayloadSchema,
  ConfirmationRequestedPayloadSchema,
} from "@/lib/schemas/sessions";
import { EVENT_TYPE, TOOL_CALL_STATUS } from "@/lib/constants";
import { PHASE_LABELS, PHASE_ITEM_KIND } from "./types";
import type { CognitivePhase, CanonizeNodeResult } from "./types";
import { buildPhaseGroups } from "./phase-utils";
import { IntentHeader } from "./IntentHeader";
import { ThoughtCard } from "./ThoughtCard";
import { ToolCallSentenceCard } from "./ToolCallSentenceCard";
import { SubagentGroupCard } from "./SubagentGroupCard";
import { FinalResponseCard } from "./FinalResponseCard";
import { ConfirmationCard } from "./ConfirmationCard";
import { MemoryBornGraph } from "./MemoryBornGraph";

const canonizeNodeArgsSchema = z.object({
  document: z.object({
    relatedEntityIds: z.array(z.string()).optional(),
    supersedes: z.string().optional(),
  }).passthrough().optional(),
  reverse_link_ids: z.array(z.string()).optional(),
}).passthrough();

const canonizeNodeResultSchema = z.object({
  status: z.string(),
  node_id: z.string().optional(),
  name: z.string().optional(),
  relationships_formed: z.number().optional(),
  note: z.string().optional(),
}).passthrough();

const STATIC_SPINE = "bg-canon-border";

interface RunGroupProps {
  events: IdentifiedEvent[];
  isLive: boolean;
}

export function RunGroup({ events, isLive }: RunGroupProps) {
  const runStarted = events.find((e) => e.type === EVENT_TYPE.RUN_STARTED);
  const invocationArgs =
    runStarted && runStarted.type === EVENT_TYPE.RUN_STARTED
      ? { request: runStarted.payload.request, context: runStarted.payload.context }
      : null;

  const confirmationResolutions = useMemo(() => {
    const map = new Map<string, ConfirmationReceivedEvent>();
    const resolved = new Set<string>();
    for (let i = events.length - 1; i >= 0; i--) {
      const e = events[i];
      if (e.type !== EVENT_TYPE.CONFIRMATION_RECEIVED) continue;
      const parsed = ConfirmationReceivedEventSchema.safeParse(e);
      if (!parsed.success) continue;
      for (let j = i - 1; j >= 0; j--) {
        const prev = events[j];
        if (prev.type !== EVENT_TYPE.CONFIRMATION_REQUESTED) continue;
        const reqParsed = ConfirmationRequestedPayloadSchema.safeParse(prev.payload);
        if (!reqParsed.success) continue;
        const cid = reqParsed.data.confirmationId;
        if (!resolved.has(cid)) {
          map.set(cid, parsed.data);
          resolved.add(cid);
        }
        break;
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
              {hasSpineBelow && <div className={`w-0.5 flex-1 min-h-2 ${STATIC_SPINE}`} />}
            </div>

            <div className="flex-1 min-w-0 pb-3">
              <PhaseLabel phase={group.phase} index={gi} />
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const idx = itemIndex++;
                  switch (item.kind) {
                    case PHASE_ITEM_KIND.THOUGHT: {
                      const parsed = ReasoningCheckpointPayloadSchema.safeParse(item.event.payload);
                      return (
                        <ThoughtCard
                          key={item.event.stableId}
                          message={parsed.success ? parsed.data.message : ""}
                          index={idx}
                        />
                      );
                    }
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
                    case PHASE_ITEM_KIND.FINAL_RESPONSE: {
                      const parsed = FinalResponsePayloadSchema.safeParse(item.event.payload);
                      return (
                        <FinalResponseCard
                          key={item.event.stableId}
                          text={parsed.success ? parsed.data.text : ""}
                          index={idx}
                        />
                      );
                    }
                    case PHASE_ITEM_KIND.CONFIRMATION_REQUESTED: {
                      const reqParsed = ConfirmationRequestedPayloadSchema.safeParse(item.event.payload);
                      const resolution = reqParsed.success
                        ? confirmationResolutions.get(reqParsed.data.confirmationId)
                        : undefined;
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
                      const argsParseResult = canonizeNodeArgsSchema.safeParse(item.pair.started.payload.args);
                      if (!argsParseResult.success) {
                        return <ToolCallSentenceCard key={item.pair.stableId} pair={item.pair} index={idx} />;
                      }
                      const args = argsParseResult.data;
                      let result: CanonizeNodeResult | undefined;
                      if (item.pair.completed !== null) {
                        const completed = item.pair.completed;
                        if (completed.payload.status === TOOL_CALL_STATUS.OK) {
                          const resultParseResult = canonizeNodeResultSchema.safeParse(completed.payload.result);
                          if (resultParseResult.success) {
                            result = resultParseResult.data;
                          }
                        }
                      }
                      if (result) {
                        return <MemoryBornGraph key={item.pair.stableId} args={args} result={result} index={idx} />;
                      }
                      return <ToolCallSentenceCard key={item.pair.stableId} pair={item.pair} index={idx} />;
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
