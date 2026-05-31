"use client";

import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import dynamic from "next/dynamic";
import type { NodeObject, LinkObject } from "react-force-graph-2d";
import { GraphStyle, tagColor } from "@/lib/graph-style";
import { drawNodeOrb, drawNodeLabel, pulseValue } from "@/lib/graph-renderer";
import { getGraph } from "@/lib/actions/graph";
import type { GraphNode } from "@/lib/schemas/graph";
import { STATUS } from "@/lib/constants";
import type { CanonizeNodeArgs, CanonizeNodeResult } from "./types";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

interface MiniGraphNode extends NodeObject {
  id: string;
  name: string;
  isNew: boolean;
  isSuperseded: boolean;
  status: string;
  tags: string[];
  connections: number;
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

const GRID_STYLE = {
  backgroundImage: `radial-gradient(circle, ${GraphStyle.GRID.DOT_COLOR} ${GraphStyle.GRID.DOT_RADIUS}px, transparent ${GraphStyle.GRID.DOT_RADIUS}px)`,
  backgroundSize: `${GraphStyle.GRID.SPACING}px ${GraphStyle.GRID.SPACING}px`,
} as const;

function SkeletonOrb({ color }: { color: string }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div
        className="rounded-full"
        style={{
          width: 16,
          height: 16,
          backgroundColor: color,
          animation: "memory-born-pulse 1.8s ease-in-out infinite",
          boxShadow: `0 0 14px ${color}66, 0 0 28px ${color}33`,
        }}
      />
    </div>
  );
}

export function MemoryBornGraph({ args, result, index }: MemoryBornGraphProps) {
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [animPhase, setAnimPhase] = useState<"loading" | "neighbors" | "node" | "edges" | "done">(
    "loading",
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(400);
  const animTimeRef = useRef(0);
  const [forceMounted, setForceMounted] = useState(false);

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

  const newNodeColor = useMemo(() => {
    const nameTag = newNodeName.toLowerCase().replace(/[^a-z0-9]/g, "-");
    return tagColor(nameTag);
  }, [newNodeName]);

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
    return () => {
      cancelled = true;
    };
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

  // Animation time tracking
  useEffect(() => {
    let raf: number;
    const loop = () => {
      animTimeRef.current = performance.now();
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  // Detect when ForceGraph2D renders its first frame
  const mountedRef = useRef(false);
  const handleFirstFrame = useCallback(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      setForceMounted(true);
    }
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
        connections: resolved?.connections ?? 0,
        fx: Math.cos(angle) * radius,
        fy: Math.sin(angle) * radius,
      });
    });

    // Add new node in center — derive hue from name so it isn't white
    if (animPhase !== "neighbors") {
      const nameTag = newNodeName.toLowerCase().replace(/[^a-z0-9]/g, "-");
      nodes.push({
        id: newNodeId,
        name: newNodeName,
        isNew: true,
        isSuperseded: false,
        status: "active",
        tags: [nameTag],
        connections: 0,
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
  }, [
    animPhase,
    allNeighborIds,
    graphNodes,
    newNodeId,
    newNodeName,
    relatedIds,
    reverseLinkIds,
    supersedesId,
  ]);

  const nodeCanvasObject = useCallback(
    (node: NodeObject, ctx: CanvasRenderingContext2D) => {
      const n = node as MiniGraphNode;
      const radius = GraphStyle.nodeRadius(n.connections);
      const x = n.x ?? 0;
      const y = n.y ?? 0;

      const isDeprecated = n.status === STATUS.DEPRECATED && !n.isSuperseded;

      drawNodeOrb(ctx, x, y, radius, {
        id: n.id,
        name: n.name,
        tags: n.tags,
        connections: n.connections,
        superseded: n.isSuperseded,
        deprecated: isDeprecated,
        pulse: n.isNew,
      }, animTimeRef.current);

      // Breathing glow ring for new node
      if (n.isNew) {
        const { ALPHA_MIN, ALPHA_MAX, PERIOD_MS } = GraphStyle.IN_PROGRESS;
        const p = pulseValue(animTimeRef.current, ALPHA_MIN, ALPHA_MAX, PERIOD_MS);
        const tagHex = tagColor(n.tags[0] ?? "");
        const r = parseInt(tagHex.slice(1, 3), 16);
        const g = parseInt(tagHex.slice(3, 5), 16);
        const b = parseInt(tagHex.slice(5, 7), 16);
        const ringOuter = radius + 6;
        const ringGrad = ctx.createRadialGradient(x, y, radius, x, y, ringOuter);
        ringGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${p})`);
        ringGrad.addColorStop(1, "rgba(0,0,0,0)");
        ctx.beginPath();
        ctx.arc(x, y, ringOuter, 0, 2 * Math.PI);
        ctx.fillStyle = ringGrad;
        ctx.fill();
      }

      drawNodeLabel(ctx, x, y, radius, n.name, n.isSuperseded, 20, 1);
    },
    [],
  );

  const linkColor = useCallback(
    (link: LinkObject) => {
      const l = link as MiniGraphLink;
      return l.type === "supersedes"
        ? GraphStyle.LINK.COLOR_SUPERSEDES
        : GraphStyle.LINK.COLOR_RELATED;
    },
    [],
  );

  const linkWidth = useCallback(
    (link: LinkObject) => {
      const l = link as MiniGraphLink;
      return l.type === "supersedes"
        ? GraphStyle.LINK.WIDTH_SUPERSEDES
        : GraphStyle.LINK.WIDTH_RELATED;
    },
    [],
  );

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      className="my-3 w-fit rounded-md border border-canon-border bg-canon-bg overflow-hidden"
    >
      <div className="h-50 w-full relative" style={GRID_STYLE}>
        <AnimatePresence mode="wait">
          {!forceMounted && (
            <motion.div
              key="skeleton"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0"
            >
              <SkeletonOrb color={newNodeColor} />
            </motion.div>
          )}
        </AnimatePresence>

        <ForceGraph2D
          width={containerWidth}
          height={200}
          graphData={{ nodes, links }}
          nodeCanvasObject={nodeCanvasObject}
          nodeCanvasObjectMode={() => "replace"}
          nodeRelSize={4}
          linkColor={linkColor}
          linkWidth={linkWidth}
          linkDirectionalParticleSpeed={() => 0}
          nodeLabel=""
          enableZoomInteraction={false}
          enablePanInteraction={false}
          enableNodeDrag={false}
          cooldownTicks={Number.MAX_SAFE_INTEGER}
          d3AlphaDecay={0}
          backgroundColor="rgba(0,0,0,0)"
          onRenderFramePost={handleFirstFrame}
        />
      </div>
      <div className="px-4 py-2.5 border-t border-canon-border">
        <p className="text-xs text-canon-text-secondary">
          Canon remembered:{" "}
          <span className="text-canon-text font-medium">&ldquo;{newNodeName}&rdquo;</span>
          {" — "}
          <span className="font-mono text-canon-text-disabled">{relationshipsFormed}</span>{" "}
          relationship{relationshipsFormed !== 1 ? "s" : ""} formed.
        </p>
      </div>
    </motion.div>
  );
}
