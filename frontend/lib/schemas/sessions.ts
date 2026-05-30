import { z } from "zod";
import { DISPLAY_KIND } from "@/lib/constants";

export const SessionResponseSchema = z.object({
  sessionId: z.string(),
  tenantId: z.string(),
  userId: z.string(),
  title: z.string(),
  summary: z.string().nullable(),
  runCount: z.number().int(),
  createdAt: z.string(),
  updatedAt: z.string(),
  lastRunAt: z.string().nullable(),
});

// ── Shared envelope fields ────────────────────────────────────────────────────

const baseEventFields = {
  author: z.string().nullable(),
  sequence: z.number().int().nullable(),
  timestamp: z.string().nullable(),
  runId: z.string(),
  isFinal: z.boolean(),
};

// ── Payload schemas ───────────────────────────────────────────────────────────

export const RunStartedPayloadSchema = z.object({ request: z.string(), context: z.string() });
export const RunCompletedPayloadSchema = z.object({});

export const ReasoningCheckpointPayloadSchema = z.object({
  message: z.string(),
});

export const FinalResponsePayloadSchema = z.object({
  text: z.string(),
});

export const SubagentInvokedPayloadSchema = z.object({
  agent_name: z.string(),
  agent_invocation_id: z.string(),
});

export const ToolCallStartedPayloadSchema = z.object({
  tool_name: z.string(),
  args: z.record(z.unknown()),
  invocation_id: z.string(),
  agent_invocation_id: z.string().nullable(),
});

export const ToolCallCompletedPayloadSchema = z.object({
  tool_name: z.string(),
  args: z.record(z.unknown()),
  result: z.unknown(),
  status: z.string(),
  invocation_id: z.string(),
  agent_invocation_id: z.string().nullable(),
});

export const ConfirmationRequestedPayloadSchema = z.object({
  confirmationId: z.string(),
  message: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  options: z.array(z.string()).optional(),
});

export const ConfirmationReceivedPayloadSchema = z.object({
  accepted: z.boolean(),
  response: z.string().optional(),
});

// ── Per-event schemas ─────────────────────────────────────────────────────────

export const RunStartedEventSchema = z.object({
  type: z.literal("run_started"),
  payload: RunStartedPayloadSchema,
  ...baseEventFields,
});

export const RunCompletedEventSchema = z.object({
  type: z.literal("run_completed"),
  payload: RunCompletedPayloadSchema,
  ...baseEventFields,
});

export const ReasoningCheckpointEventSchema = z.object({
  type: z.literal("reasoning_checkpoint"),
  payload: ReasoningCheckpointPayloadSchema,
  ...baseEventFields,
});

export const FinalResponseEventSchema = z.object({
  type: z.literal("final_response"),
  payload: FinalResponsePayloadSchema,
  ...baseEventFields,
});

export const SubagentInvokedEventSchema = z.object({
  type: z.literal("subagent_invoked"),
  payload: SubagentInvokedPayloadSchema,
  ...baseEventFields,
});

export const ToolCallStartedEventSchema = z.object({
  type: z.literal("tool_call_started"),
  payload: ToolCallStartedPayloadSchema,
  ...baseEventFields,
});

export const ToolCallCompletedEventSchema = z.object({
  type: z.literal("tool_call_completed"),
  payload: ToolCallCompletedPayloadSchema,
  ...baseEventFields,
});

export const ConfirmationRequestedEventSchema = z.object({
  type: z.literal("confirmation_requested"),
  payload: ConfirmationRequestedPayloadSchema,
  ...baseEventFields,
});

export const ConfirmationReceivedEventSchema = z.object({
  type: z.literal("confirmation_received"),
  payload: ConfirmationReceivedPayloadSchema,
  ...baseEventFields,
});

// ── Discriminated union ───────────────────────────────────────────────────────

export const AgentEventSchema = z.discriminatedUnion("type", [
  RunStartedEventSchema,
  RunCompletedEventSchema,
  ReasoningCheckpointEventSchema,
  FinalResponseEventSchema,
  SubagentInvokedEventSchema,
  ToolCallStartedEventSchema,
  ToolCallCompletedEventSchema,
  ConfirmationRequestedEventSchema,
  ConfirmationReceivedEventSchema,
]);

// ── Display-layer schemas ─────────────────────────────────────────────────────

// stableId is assigned on the frontend for stable React keys.
const identifiedEventFields = { kind: z.literal(DISPLAY_KIND.EVENT), stableId: z.number() };

export const IdentifiedEventSchema = AgentEventSchema.and(z.object(identifiedEventFields));

// Pairs a tool_call_started with its matching tool_call_completed (same invocation_id).
// completed is null while the tool is still running.
export const ToolCallPairSchema = z.object({
  kind: z.literal(DISPLAY_KIND.TOOL_CALL_PAIR),
  stableId: z.number(),
  invocationId: z.string(),
  started: ToolCallStartedEventSchema.extend(identifiedEventFields),
  completed: ToolCallCompletedEventSchema.extend(identifiedEventFields).nullable(),
});

export const SubagentGroupSchema = z.object({
  kind: z.literal(DISPLAY_KIND.SUBAGENT_GROUP),
  stableId: z.number(),
  agentInvocationId: z.string(),
  agentName: z.string(),
  timestamp: z.string().nullable(),
  toolPairs: z.array(ToolCallPairSchema),
  checkpoints: z.array(ReasoningCheckpointEventSchema.extend(identifiedEventFields)).default([]),
});

// z.union instead of z.discriminatedUnion because IdentifiedEventSchema is an
// intersection (ZodIntersection), not a plain ZodObject. TypeScript still narrows
// correctly on `kind` because all inferred types carry it as a literal.
export const DisplayItemSchema = z.union([
  IdentifiedEventSchema,
  ToolCallPairSchema,
  SubagentGroupSchema,
]);

// ── TypeScript types ──────────────────────────────────────────────────────────

export const SessionListResponseSchema = z.object({
  sessions: z.array(SessionResponseSchema),
  total: z.number().int(),
  nextCursor: z.string().nullable(),
});

export type SessionResponse = z.infer<typeof SessionResponseSchema>;
export type SessionListResponse = z.infer<typeof SessionListResponseSchema>;
export type AgentEvent = z.infer<typeof AgentEventSchema>;
export type RunStartedEvent = z.infer<typeof RunStartedEventSchema>;
export type RunCompletedEvent = z.infer<typeof RunCompletedEventSchema>;
export type ReasoningCheckpointEvent = z.infer<typeof ReasoningCheckpointEventSchema>;
export type FinalResponseEvent = z.infer<typeof FinalResponseEventSchema>;
export type SubagentInvokedEvent = z.infer<typeof SubagentInvokedEventSchema>;
export type ToolCallStartedEvent = z.infer<typeof ToolCallStartedEventSchema>;
export type ToolCallCompletedEvent = z.infer<typeof ToolCallCompletedEventSchema>;
export type ConfirmationRequestedEvent = z.infer<typeof ConfirmationRequestedEventSchema>;
export type ConfirmationReceivedEvent = z.infer<typeof ConfirmationReceivedEventSchema>;
export type IdentifiedEvent = z.infer<typeof IdentifiedEventSchema>;
export type ToolCallPair = z.infer<typeof ToolCallPairSchema>;
export type SubagentGroup = z.infer<typeof SubagentGroupSchema>;
export type DisplayItem = z.infer<typeof DisplayItemSchema>;
