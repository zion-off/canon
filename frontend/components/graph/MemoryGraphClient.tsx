"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { NodeObject, LinkObject } from "react-force-graph-2d";
import type { GraphNode, GraphLink } from "@/lib/schemas/graph";
import { GraphStyle } from "@/lib/graph-style";
import { STATUS } from "@/lib/constants";
import { GraphFilters } from "./GraphFilters";
import { NodeDetailPanel } from "./NodeDetailPanel";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

type GraphNodeFG = GraphNode & NodeObject & { x?: number; y?: number };
type GraphLinkFG = GraphLink & LinkObject;

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface MemoryGraphClientProps {
  graphData: GraphData;
}

// ---------------------------------------------------------------------------
// Animated node renderer
// ---------------------------------------------------------------------------

function renderNode(
  node: GraphNodeFG,
  ctx: CanvasRenderingContext2D,
  globalScale: number,
  isHighlighted: boolean,
  isSearchMatch: boolean,
  time: number,
): void {
  const radius = GraphStyle.nodeRadius(node.connections ?? 0);
  const x = node.x ?? 0;
  const y = node.y ?? 0;

  const isSuperseded = !!node.supersededBy;
  const isDeprecated = node.status === STATUS.DEPRECATED && !node.supersededBy;
  const isInProgress = node.status === STATUS.IN_PROGRESS && !node.supersededBy;
  const isRecent =
    !isSuperseded &&
    !isDeprecated &&
    Date.now() - new Date(node.updatedAt).getTime() < GraphStyle.RECENT.WINDOW_MS;

  const tagColor = GraphStyle.nodeBaseColor(node);
  const r = parseInt(tagColor.slice(1, 3), 16);
  const g = parseInt(tagColor.slice(3, 5), 16);
  const b = parseInt(tagColor.slice(5, 7), 16);

  // Dim factor for deprecated / superseded
  const dimAlpha = isSuperseded
    ? GraphStyle.SUPERSEDED_ALPHA
    : isDeprecated
      ? GraphStyle.DEPRECATED_ALPHA
      : 1;

  // ---- Orb fill with radial gradient ----
  // Subtle highlight at centre, darker rim for depth
  const highlightMix = 0.25;
  const hlR = Math.round(r + (255 - r) * highlightMix);
  const hlG = Math.round(g + (255 - g) * highlightMix);
  const hlB = Math.round(b + (255 - b) * highlightMix);
  const rimR = Math.round(r * 0.55);
  const rimG = Math.round(g * 0.55);
  const rimB = Math.round(b * 0.55);

  const grad = ctx.createRadialGradient(
    x - radius * GraphStyle.SPECULAR_OFFSET_RATIO,
    y - radius * GraphStyle.SPECULAR_OFFSET_RATIO,
    0,
    x,
    y,
    radius,
  );

  if (isInProgress) {
    const { ALPHA_MIN, ALPHA_MAX, PERIOD_MS } = GraphStyle.IN_PROGRESS;
    const t = (time % PERIOD_MS) / PERIOD_MS;
    const ease = 0.5 - 0.5 * Math.cos(2 * Math.PI * t);
    const pulse = (ALPHA_MIN + ease * (ALPHA_MAX - ALPHA_MIN)) * dimAlpha;
    grad.addColorStop(0, `rgba(${hlR}, ${hlG}, ${hlB}, ${pulse})`);
    grad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${pulse})`);
    grad.addColorStop(1, `rgba(${rimR}, ${rimG}, ${rimB}, ${pulse})`);
  } else {
    grad.addColorStop(0, `rgba(${hlR}, ${hlG}, ${hlB}, ${dimAlpha})`);
    grad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${dimAlpha})`);
    grad.addColorStop(1, `rgba(${rimR}, ${rimG}, ${rimB}, ${dimAlpha})`);
  }

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, 2 * Math.PI);
  ctx.fillStyle = grad;
  ctx.fill();

  // ---- Specular highlight dot ----
  const specR = radius * GraphStyle.SPECULAR_DOT_RATIO;
  if (specR > 1) {
    const sx = x - radius * GraphStyle.SPECULAR_OFFSET_RATIO;
    const sy = y - radius * GraphStyle.SPECULAR_OFFSET_RATIO;
    ctx.beginPath();
    ctx.arc(sx, sy, specR, 0, 2 * Math.PI);
    ctx.fillStyle = "rgba(255, 255, 255, 0.2)";
    ctx.fill();
  }

  // ---- Recent update ring pulse ----
  if (isRecent) {
    const { ALPHA_MAX, PERIOD_MS } = GraphStyle.RECENT;
    const t = (time % PERIOD_MS) / PERIOD_MS;
    const ease = 0.5 - 0.5 * Math.cos(2 * Math.PI * t);
    const alpha = ease * ALPHA_MAX;
    const ringOuter = radius + 6;

    const ringGrad = ctx.createRadialGradient(x, y, radius, x, y, ringOuter);
    ringGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha})`);
    ringGrad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.beginPath();
    ctx.arc(x, y, ringOuter, 0, 2 * Math.PI);
    ctx.fillStyle = ringGrad;
    ctx.fill();
  }

  // ---- Search-match breathing ring ----
  if (isSearchMatch) {
    const { ALPHA_MIN, ALPHA_MAX, PERIOD_MS } = GraphStyle.SEARCH;
    const t = (time % PERIOD_MS) / PERIOD_MS;
    const ease = 0.5 - 0.5 * Math.cos(2 * Math.PI * t);
    const alpha = ALPHA_MIN + ease * (ALPHA_MAX - ALPHA_MIN);
    const ringOuter = radius + 6;

    const ringGrad = ctx.createRadialGradient(x, y, radius, x, y, ringOuter);
    ringGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha})`);
    ringGrad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.beginPath();
    ctx.arc(x, y, ringOuter, 0, 2 * Math.PI);
    ctx.fillStyle = ringGrad;
    ctx.fill();
  }

  // ---- Highlight ring (selected / hovered) ----
  if (isHighlighted && !isSearchMatch) {
    ctx.beginPath();
    ctx.arc(x, y, radius + 4, 0, 2 * Math.PI);
    ctx.strokeStyle = GraphStyle.HIGHLIGHT.COLOR;
    ctx.lineWidth = GraphStyle.HIGHLIGHT.WIDTH / globalScale;
    ctx.stroke();
  }

  // ---- Label ----
  if (globalScale > GraphStyle.LABEL.SCALE_THRESHOLD) {
    const label = node.name.slice(0, GraphStyle.LABEL.MAX_CHARS);
    ctx.font = `${11 / globalScale}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = GraphStyle.LABEL.COLOR;
    ctx.fillText(label, x, y + radius + 2 / globalScale);
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MemoryGraphClient({ graphData }: MemoryGraphClientProps) {
  const [tagFilter, setTagFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNodeFG | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const graphContainerRef = useRef<HTMLDivElement>(null);
  const animTimeRef = useRef(0);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // ---- Animation time tracking ----
  useEffect(() => {
    let raf: number;
    const loop = () => {
      animTimeRef.current = performance.now();
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  // ---- Dimensions ----
  useEffect(() => {
    const measure = () => {
      if (graphContainerRef.current) {
        const { width: w, height: h } = graphContainerRef.current.getBoundingClientRect();
        if (w > 0 && h > 0) {
          setDimensions({ width: w, height: h });
        }
      }
    };

    measure();
    const ro = new ResizeObserver(measure);
    if (graphContainerRef.current) {
      ro.observe(graphContainerRef.current);
    }
    return () => ro.disconnect();
  }, []);

  const { width, height } = dimensions;

  // ---- Tags ----
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    graphData.nodes.forEach((n) => n.tags.forEach((t) => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [graphData.nodes]);

  // ---- Filters ----
  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;

    if (tagFilter) {
      nodes = nodes.filter((n) =>
        n.tags.some((t) => t.toLowerCase().includes(tagFilter.toLowerCase())),
      );
    }

    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = graphData.links.filter((l) => {
      const src =
        typeof l.source === "object" ? (l.source as GraphNodeFG).id : (l.source as string);
      const tgt =
        typeof l.target === "object" ? (l.target as GraphNodeFG).id : (l.target as string);
      return nodeIds.has(src) && nodeIds.has(tgt);
    });

    return { nodes, links };
  }, [graphData, tagFilter]);

  // ---- Search matches ----
  const searchHighlightIds = useMemo(() => {
    if (!searchQuery.trim()) return new Set<string>();
    const q = searchQuery.toLowerCase();
    return new Set(
      filteredData.nodes
        .filter(
          (n) =>
            n.name.toLowerCase().includes(q) ||
            n.description.toLowerCase().includes(q) ||
            n.tags.some((t) => t.toLowerCase().includes(q)),
        )
        .map((n) => n.id),
    );
  }, [filteredData.nodes, searchQuery]);

  // ---- Connected nodes ----
  const connectedNodeIds = useMemo(() => {
    if (!selectedNodeId) return [];
    const ids = new Set<string>();
    graphData.links.forEach((link) => {
      const src = typeof link.source === "object" ? (link.source as GraphNodeFG).id : link.source;
      const tgt = typeof link.target === "object" ? (link.target as GraphNodeFG).id : link.target;
      if (src === selectedNodeId) ids.add(tgt);
      if (tgt === selectedNodeId) ids.add(src);
    });
    return Array.from(ids);
  }, [selectedNodeId, graphData.links]);

  const selectedNode = useMemo(
    () => graphData.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [graphData.nodes, selectedNodeId],
  );

  // ---- Handlers ----
  const handleNodeClick = useCallback((node: NodeObject) => {
    setSelectedNodeId((node as GraphNodeFG).id);
  }, []);

  const handleNodeHover = useCallback((node: NodeObject | null) => {
    setHoveredNode(node as GraphNodeFG | null);
  }, []);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (hoveredNode && graphContainerRef.current) {
        const rect = graphContainerRef.current.getBoundingClientRect();
        setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
      }
    },
    [hoveredNode],
  );

  // ---- Canvas node rendering ----
  const nodeCanvasObject = useCallback(
    (node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const gNode = node as GraphNodeFG;
      const isSelected = gNode.id === selectedNodeId;
      const isHovered = gNode.id === hoveredNode?.id;
      const isSearch = searchHighlightIds.size > 0 && searchHighlightIds.has(gNode.id);
      const isHighlighted = isSelected || isHovered;
      renderNode(gNode, ctx, globalScale, isHighlighted, isSearch, animTimeRef.current);
    },
    [selectedNodeId, hoveredNode, searchHighlightIds],
  );

  // ---- Canvas link rendering ----
  const isSupersedes = (link: LinkObject) => (link as GraphLinkFG).type === "supersedes";

  const linkColor = useCallback(
    (link: LinkObject) =>
      isSupersedes(link) ? GraphStyle.LINK.COLOR_SUPERSEDES : GraphStyle.LINK.COLOR_RELATED,
    [],
  );

  const linkWidth = useCallback(
    (link: LinkObject) =>
      isSupersedes(link) ? GraphStyle.LINK.WIDTH_SUPERSEDES : GraphStyle.LINK.WIDTH_RELATED,
    [],
  );

  const linkDirectionalParticles = useCallback(
    (link: LinkObject) => (isSupersedes(link) ? GraphStyle.LINK.SUPERSEDES_PARTICLE_COUNT : 0),
    [],
  );

  const linkDirectionalParticleSpeed = useCallback(
    (link: LinkObject) => (isSupersedes(link) ? GraphStyle.LINK.SUPERSEDES_PARTICLE_SPEED : 0),
    [],
  );

  const linkDirectionalParticleWidth = useCallback(
    (link: LinkObject) => (isSupersedes(link) ? GraphStyle.LINK.SUPERSEDES_PARTICLE_WIDTH : 0),
    [],
  );

  const linkDirectionalParticleColor = useCallback(() => GraphStyle.LINK.COLOR_SUPERSEDES, []);

  return (
    <div className="flex h-full flex-col">
      <GraphFilters
        tagFilter={tagFilter}
        onTagChange={setTagFilter}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        allTags={allTags}
        nodeCount={filteredData.nodes.length}
        linkCount={filteredData.links.length}
      />

      <div className="flex min-h-0 flex-1">
        <div
          ref={graphContainerRef}
          className={`relative min-h-0 ${selectedNode ? "w-[65%]" : "w-full"}`}
          onMouseMove={handleMouseMove}
        >
          <ForceGraph2D
            graphData={filteredData}
            nodeCanvasObject={nodeCanvasObject}
            nodeCanvasObjectMode={() => "replace"}
            nodeRelSize={4}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
            linkColor={linkColor}
            linkWidth={linkWidth}
            linkDirectionalParticles={linkDirectionalParticles}
            linkDirectionalParticleSpeed={linkDirectionalParticleSpeed}
            linkDirectionalParticleWidth={linkDirectionalParticleWidth}
            linkDirectionalParticleColor={linkDirectionalParticleColor}
            nodeLabel=""
            width={width}
            height={height}
            backgroundColor={GraphStyle.BG}
            cooldownTicks={Number.MAX_SAFE_INTEGER}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.4}
          />

          {hoveredNode && (
            <div
              className="pointer-events-none absolute z-50 max-w-64 border border-canon-border bg-canon-surface px-3 py-2"
              style={{
                left: tooltipPos.x + 12,
                top: tooltipPos.y - 8,
              }}
            >
              <p className="text-sm font-medium text-canon-text">{hoveredNode.name}</p>
              <p className="mt-0.5 text-xs text-canon-text-secondary">
                {hoveredNode.status} · {hoveredNode.connections} connections
              </p>
              {hoveredNode.tags.length > 0 && (
                <p className="mt-1 text-xs text-canon-text-secondary">
                  {hoveredNode.tags.slice(0, 3).join(", ")}
                </p>
              )}
            </div>
          )}
        </div>

        {selectedNode && (
          <div className="w-[35%]">
            <NodeDetailPanel
              node={selectedNode}
              allNodes={graphData.nodes}
              connectedNodeIds={connectedNodeIds}
              onClose={() => setSelectedNodeId(null)}
              onSelectNode={setSelectedNodeId}
            />
          </div>
        )}
      </div>
    </div>
  );
}
