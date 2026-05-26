import { z } from "zod";

export const SessionResponseSchema = z.object({
  sessionId: z.string(),
  title: z.string(),
  summary: z.string().nullable(),
  runCount: z.number().int(),
  createdAt: z.string(),
  updatedAt: z.string(),
  lastRunAt: z.string().nullable(),
});

export const AgentEventTypeSchema = z.enum([
  "reasoning_checkpoint",
  "tool_call_started",
  "tool_call_completed",
  "subagent_invoked",
  "run_started",
  "run_completed",
  "final_response",
]);

export const AgentEventSchema = z.object({
  type: AgentEventTypeSchema,
  author: z.string().nullable(),
  content: z.string().nullable(),
  sequence: z.number().int().nullable(),
  timestamp: z.string().nullable(),
  isFinal: z.boolean(),
});

export type SessionResponse = z.infer<typeof SessionResponseSchema>;
export type AgentEventType = z.infer<typeof AgentEventTypeSchema>;
export type AgentEvent = z.infer<typeof AgentEventSchema>;
