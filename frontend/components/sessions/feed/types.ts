import type {
  IdentifiedEvent,
  ToolCallPair,
  SubagentGroup,
} from "@/lib/schemas/sessions";

// Cognitive phases inferred from the event stream
export type CognitivePhase =
  | "perceiving"
  | "reasoning"
  | "tracing"
  | "reshaping"
  | "remembering";

export const PHASE_LABELS: Record<CognitivePhase, string> = {
  perceiving: "Perceiving",
  reasoning: "Reasoning",
  tracing: "Tracing",
  reshaping: "Reshaping",
  remembering: "Remembering",
};

export const PHASE_DESCRIPTIONS: Record<CognitivePhase, string> = {
  perceiving: "Consulting organizational memory",
  reasoning: "Processing and evaluating",
  tracing: "Exploring relationships",
  reshaping: "Formulating response",
  remembering: "Forming new memory",
};

// A phased group of display items
export interface PhaseGroup {
  phase: CognitivePhase;
  items: PhaseItem[];
}

export type PhaseItem =
  | { kind: "thought"; event: IdentifiedEvent & { type: "reasoning_checkpoint" } }
  | { kind: "tool-pair"; pair: ToolCallPair }
  | { kind: "subagent-group"; group: SubagentGroup }
  | { kind: "final-response"; event: IdentifiedEvent & { type: "final_response" } }
  | { kind: "confirmation-requested"; event: IdentifiedEvent & { type: "confirmation_requested" } }
  | { kind: "confirmation-received"; event: IdentifiedEvent & { type: "confirmation_received" } }
  | { kind: "canonize-pair"; pair: ToolCallPair };

// Confirmation state tracker
export interface ConfirmationState {
  confirmationId: string;
  title?: string;
  description?: string;
  message?: string;
  options?: string[];
  resolved: boolean;
  accepted?: boolean;
}

// Search result item shape from hybrid_search
export interface SearchResultItem {
  _id: string;
  name: string;
  description?: string;
  status?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

// Canonize args shape
export interface CanonizeNodeArgs {
  document?: {
    relatedEntityIds?: string[];
    supersedes?: string;
    [key: string]: unknown;
  };
  reverse_link_ids?: string[];
  [key: string]: unknown;
}

// Canonize result shape
export interface CanonizeNodeResult {
  status: string;
  node_id?: string;
  name?: string;
  relationships_formed?: number;
  note?: string;
  [key: string]: unknown;
}
