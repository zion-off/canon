import type {
  IdentifiedEvent,
  ToolCallPair,
  SubagentGroup,
} from "@/lib/schemas/sessions";

// Cognitive phases inferred from the event stream
export const COGNITIVE_PHASE = {
  PERCEIVING: "perceiving",
  REASONING: "reasoning",
  TRACING: "tracing",
  RESHAPING: "reshaping",
  REMEMBERING: "remembering",
} as const;

export type CognitivePhase = typeof COGNITIVE_PHASE[keyof typeof COGNITIVE_PHASE];

export const PHASE_LABELS: Record<CognitivePhase, string> = {
  [COGNITIVE_PHASE.PERCEIVING]: "Perceiving",
  [COGNITIVE_PHASE.REASONING]: "Reasoning",
  [COGNITIVE_PHASE.TRACING]: "Tracing",
  [COGNITIVE_PHASE.RESHAPING]: "Reshaping",
  [COGNITIVE_PHASE.REMEMBERING]: "Remembering",
};

export const PHASE_DESCRIPTIONS: Record<CognitivePhase, string> = {
  [COGNITIVE_PHASE.PERCEIVING]: "Consulting organizational memory",
  [COGNITIVE_PHASE.REASONING]: "Processing and evaluating",
  [COGNITIVE_PHASE.TRACING]: "Exploring relationships",
  [COGNITIVE_PHASE.RESHAPING]: "Formulating response",
  [COGNITIVE_PHASE.REMEMBERING]: "Forming new memory",
};

// A phased group of display items
export const PHASE_ITEM_KIND = {
  THOUGHT: "thought",
  TOOL_PAIR: "tool-pair",
  SUBAGENT_GROUP: "subagent-group",
  FINAL_RESPONSE: "final-response",
  CONFIRMATION_REQUESTED: "confirmation-requested",
  CONFIRMATION_RECEIVED: "confirmation-received",
  CANONIZE_PAIR: "canonize-pair",
} as const;

export type PhaseItemKind = typeof PHASE_ITEM_KIND[keyof typeof PHASE_ITEM_KIND];

export interface PhaseGroup {
  phase: CognitivePhase;
  items: PhaseItem[];
}

export type PhaseItem =
  | { kind: typeof PHASE_ITEM_KIND.THOUGHT; event: IdentifiedEvent }
  | { kind: typeof PHASE_ITEM_KIND.TOOL_PAIR; pair: ToolCallPair }
  | { kind: typeof PHASE_ITEM_KIND.SUBAGENT_GROUP; group: SubagentGroup }
  | { kind: typeof PHASE_ITEM_KIND.FINAL_RESPONSE; event: IdentifiedEvent }
  | { kind: typeof PHASE_ITEM_KIND.CONFIRMATION_REQUESTED; event: IdentifiedEvent }
  | { kind: typeof PHASE_ITEM_KIND.CONFIRMATION_RECEIVED; event: IdentifiedEvent }
  | { kind: typeof PHASE_ITEM_KIND.CANONIZE_PAIR; pair: ToolCallPair };

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
