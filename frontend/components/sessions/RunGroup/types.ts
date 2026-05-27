import type { DisplayItem, ToolCallPair } from "@/lib/schemas/sessions";

export type PairLocation =
  | { kind: "top-level"; idx: number }
  | { kind: "in-group"; groupIdx: number; pairIdx: number };

export type CanonizeInvocationSlot = {
  variant: "canonize-invocation";
  pair: ToolCallPair;
};

export type CanonizeCompletionSlot = {
  variant: "canonize-completion";
  pair: ToolCallPair;
};

export type DisplayItemSlot = {
  variant: "display-item";
  item: DisplayItem;
};

export type TimelineSlotItem = CanonizeInvocationSlot | CanonizeCompletionSlot | DisplayItemSlot;
