"use client";

import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { motion } from "motion/react";
import dynamic from "next/dynamic";
import type { NodeObject, LinkObject } from "react-force-graph-2d";
import { GraphStyle } from "@/lib/graph-style";
import { getGraph } from "@/lib/actions/graph";
import type { GraphNode } from "@/lib/schemas/graph";
import type { CanonizeNodeArgs, CanonizeNodeResult } from "./types";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

interface MiniGraphNode extends NodeObject {
  id: string;
  name: string;
  isNew: boolean;
  isSuperseded: boolean;
  status: string;
  tags: string[];
  fx?: number;
  fy?: number;
}

interface MiniGraphLink extends LinkObject {
  source: string;
  target: string;
  type: "related" | "supersedes";
}

interface MemoryBornGraphProps {
  args: CanonizeNodeArgs;
  result: CanonizeNodeResult;
  index: number;
}

export function MemoryBornGraph({ args, result, index }: MemoryBornGraphProps) {
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [animPhase, setAnimPhase] = useState<"loading" | "neighbors" | "node" | "edges" | "done">("loading");
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(400);

  const newNodeId = result.node_id ?? "new-node";
  const newNodeName = result.name ?? "New Memory";
  const relatedIds = useMemo(() => args.document?.relatedEntityIds ?? [], [args]);
  const supersedesId = args.document?.supersedes ?? null;
  const reverseLinkIds = useMemo(() => args.reverse_link_ids ?? [], [args]);
  const allNeighborIds = useMemo(
    () => [...new Set([...relatedIds, ...reverseLinkIds, ...(supersedesId ? [supersedesId] : [])])],
    [relatedIds, reverseLinkIds, supersedesId],
  );
  const relationshipsFormed = result.relationships_formed ?? allNeighborIds.length;

  useEffect(() => {
    let cancelled = false;
    async function loadGraph() {
      try {
        const data = await getGraph();
        if (!cancelled) setGraphNodes(data.nodes);
      } catch {
        // proceed without full graph data
      }
    }
    loadGraph();
    return () => { cancelled = true; };
  }, []);

  // Track container width for full-bleed graph
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setContainerWidth(entry.contentRect.width);
    });
    ro.observe(el);
    setContainerWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  // Run animation phases
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    timers.push(setTimeout(() => setAnimPhase("neighbors"), 300));
    timers.push(setTimeout(() => setAnimPhase("node"), 900));
    timers.push(setTimeout(() => setAnimPhase("edges"), 1400));
    timers.push(setTimeout(() => setAnimPhase("done"), 2200));
    return () => timers.forEach(clearTimeout);
  }, []);

  // Build graph data for force-graph
  const { nodes, links } = useMemo(() => {
    const nodes: MiniGraphNode[] = [];
    const links: MiniGraphLink[] = [];

    if (animPhase === "loading") return { nodes, links };

    // Seed positions deterministically in a circle
    const angleStep = (2 * Math.PI) / Math.max(allNeighborIds.length, 1);
    const radius = 60;

    // Add neighbor nodes
    allNeighborIds.forEach((id, i) => {
      const resolved = graphNodes.find((n) => n.id === id);
      const angle = angleStep * i;
      nodes.push({
        id,
        name: resolved?.name ?? id.slice(0, 8),
        isNew: false,
        isSuperseded: id === supersedesId,
        status: id === supersedesId ? "deprecated" : (resolved?.status ?? "active"),
        tags: resolved?.tags ?? [],
        fx: Math.cos(angle) * radius,
        fy: Math.sin(angle) * radius,
      });
    });

    // Add new node in center
    if (animPhase !== "neighbors") {
      nodes.push({
        id: newNodeId,
        name: newNodeName,
        isNew: true,
        isSuperseded: false,
        status: "active",
        tags: [],
        fx: 0,
        fy: 0,
      });
    }

    // Add edges
    if (animPhase === "edges" || animPhase === "done") {
      for (const id of relatedIds) {
        links.push({ source: newNodeId, target: id, type: "related" });
      }
      for (const id of reverseLinkIds) {
        if (!relatedIds.includes(id)) {
          links.push({ source: id, target: newNodeId, type: "related" });
        }
      }
      if (supersedesId) {
        links.push({ source: newNodeId, target: supersedesId, type: "supersedes" });
      }
    }

    return { nodes, links };
  }, [animPhase, allNeighborIds, graphNodes, newNodeId, newNodeName, relatedIds, reverseLinkIds, supersedesId]);

  const nodeCanvasObject = useCallback((node: NodeObject, ctx: CanvasRenderingContext2D) => {
    const n = node as MiniGraphNode;
    const x = n.x ?? 0;
    const y = n.y ?? 0;
    const baseRadius = n.isNew ? 8 : 5;
    const color = n.isNew ? "#ffffff" : GraphStyle.nodeBaseColor({ tags: n.tags });
    const alpha = n.isSuperseded ? GraphStyle.SUPERSEDED_ALPHA : 1;

    ctx.save();
    ctx.globalAlpha = alpha;

    // Node circle
    ctx.beginPath();
    ctx.arc(x, y, baseRadius, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Accent ring for new node
    if (n.isNew) {
      ctx.beginPath();
      ctx.arc(x, y, baseRadius + 3, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.6)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Label
    ctx.font = "9px JetBrains Mono, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = n.isSuperseded ? "rgba(212,212,212,0.3)" : "rgba(212,212,212,0.85)";
    const label = n.name.length > 20 ? n.name.slice(0, 19) + "…" : n.name;
    ctx.fillText(label, x, y + baseRadius + 4);

    ctx.restore();
  }, []);

  const linkCanvasObject = useCallback((link: LinkObject, ctx: CanvasRenderingContext2D) => {
    const l = link as MiniGraphLink & { source: MiniGraphNode; target: MiniGraphNode };
    if (!l.source?.x || !l.target?.x) return;

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(l.source.x, l.source.y ?? 0);
    ctx.lineTo(l.target.x, l.target.y ?? 0);
    ctx.strokeStyle = l.type === "supersedes"
      ? GraphStyle.LINK.COLOR_SUPERSEDES
      : GraphStyle.LINK.COLOR_RELATED;
    ctx.lineWidth = l.type === "supersedes"
      ? GraphStyle.LINK.WIDTH_SUPERSEDES
      : GraphStyle.LINK.WIDTH_RELATED;
    ctx.stroke();
    ctx.restore();
  }, []);

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      className="my-3 rounded-md border border-canon-border bg-canon-bg overflow-hidden"
    >
      <div className="h-[200px] w-full">
        <ForceGraph2D
          width={containerWidth}
          height={200}
          graphData={{ nodes, links }}
          nodeCanvasObject={nodeCanvasObject}
          linkCanvasObject={linkCanvasObject}
          enableZoomInteraction={false}
          enablePanInteraction={false}
          enableNodeDrag={false}
          cooldownTime={0}
          d3AlphaDecay={1}
          d3VelocityDecay={1}
          backgroundColor="transparent"
        />
      </div>
      <div className="px-4 py-2.5 border-t border-canon-border">
        <p className="text-xs text-canon-text-secondary">
          Canon remembered: <span className="text-canon-text font-medium">&ldquo;{newNodeName}&rdquo;</span>
          {" — "}
          <span className="font-mono text-canon-text-disabled">{relationshipsFormed}</span> relationship{relationshipsFormed !== 1 ? "s" : ""} formed.
        </p>
      </div>
    </motion.div>
  );
}
