"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";
import type { GraphNode } from "@/lib/schemas/graph";
import { NodeDetailPanel } from "@/components/graph/NodeDetailPanel";
import { getGraph } from "@/lib/actions/graph";

interface MemoryChipsProps {
  results: Record<string, unknown>[];
}

const MORPH_TRANSITION = {
  duration: 0.5,
  ease: [0.25, 0.1, 0.25, 1] as const,
};

export function MemoryChips({ results }: MemoryChipsProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<{
    nodes: GraphNode[];
    links: { source: string; target: string; type: string }[];
  } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChipClick = async (nodeId: string) => {
    setSelectedNodeId(nodeId);
    if (!graphData) {
      setLoading(true);
      try {
        const data = await getGraph();
        setGraphData(data);
      } catch {
        // Graph fetch failed — still show what we can
      } finally {
        setLoading(false);
      }
    }
  };

  const selectedNode = graphData?.nodes.find((n) => n.id === selectedNodeId) ?? null;
  const connectedNodeIds = graphData
    ? graphData.links
        .filter((l) => l.source === selectedNodeId || l.target === selectedNodeId)
        .map((l) => (l.source === selectedNodeId ? l.target : l.source))
    : [];

  const isPanelOpen = selectedNode !== null && graphData !== null;

  return (
    <>
      <motion.div layout className="flex flex-wrap gap-1.5">
        <AnimatePresence mode="popLayout">
          {results.slice(0, 8).map((item, i) => {
            const id = (item._id as string) ?? (item.id as string) ?? `result-${i}`;
            const name = (item.name as string) ?? "Unnamed";
            const status = (item.status as string) ?? "active";
            const tags = (item.tags as string[]) ?? [];
            const isDeprecated = status === "deprecated";
            const isSuperseded = !!item.supersededBy;
            const isSelected = id === selectedNodeId && isPanelOpen;

            if (isSelected) return null;

            return (
              <motion.button
                key={id}
                layoutId={id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: isDeprecated || isSuperseded ? 0.4 : 1, scale: 1 }}
                exit={{ opacity: 0, filter: "blur(6px)", scale: 1.05 }}
                transition={{ duration: 0.2, delay: i * 0.03 }}
                onClick={() => handleChipClick(id)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-canon-border
                  bg-canon-surface-raised hover:bg-canon-border/50 transition-colors cursor-pointer
                  ${isDeprecated || isSuperseded ? "opacity-40" : ""}`}
              >
                <span className="text-xs text-canon-text truncate max-w-40">{name}</span>
                <Badge variant={status as BadgeVariant}>{status}</Badge>
                {tags.slice(0, 2).map((tag) => (
                  <span key={tag} className="text-[10px] text-canon-text-disabled font-mono">
                    #{tag}
                  </span>
                ))}
              </motion.button>
            );
          })}
        </AnimatePresence>
        {results.length > 8 && (
          <span className="text-xs text-canon-text-disabled self-center ml-1">
            +{results.length - 8} more
          </span>
        )}
      </motion.div>

      <AnimatePresence mode="wait">
        {isPanelOpen && selectedNodeId && (
          <motion.div
            key={`panel-${selectedNodeId}`}
            layoutId={selectedNodeId}
            initial={{ opacity: 0, filter: "blur(6px)" }}
            animate={{ opacity: 1, filter: "blur(0px)" }}
            exit={{ opacity: 0, filter: "blur(6px)", scale: 0.98 }}
            transition={MORPH_TRANSITION}
            className="mt-3 border border-canon-border rounded-md bg-canon-surface overflow-hidden"
          >
            <div className="max-h-100 overflow-y-auto">
              <NodeDetailPanel
                node={selectedNode!}
                allNodes={graphData.nodes}
                connectedNodeIds={connectedNodeIds}
                onClose={() => setSelectedNodeId(null)}
                onSelectNode={(nodeId) => setSelectedNodeId(nodeId)}
                onNodeUpdated={() => {}}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {selectedNodeId && !selectedNode && !loading && (
        <p className="mt-2 text-xs text-canon-text-secondary">
          Node details unavailable — document may not be in graph view.
        </p>
      )}

      {loading && (
        <p className="mt-2 text-xs text-canon-text-secondary italic">Loading node details…</p>
      )}
    </>
  );
}
