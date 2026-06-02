"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { NodeObject, LinkObject } from "react-force-graph-2d";
import type { GraphNode, GraphLink } from "@/lib/schemas/graph";
import { GraphStyle } from "@/lib/graph-style";
import { drawNodeOrb, drawNodeLabel, pulseValue } from "@/lib/graph-renderer";
import { KNOWN_STATUS } from "@/lib/constants";
import { GraphFilters } from "./GraphFilters";
import { NodeDetailPanel } from "./NodeDetailPanel";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

type GraphNodeFG = GraphNode & NodeObject & { x?: number; y?: number };

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface MemoryGraphClientProps {
  graphData: GraphData;
}

// ---------------------------------------------------------------------------
// Animated node renderer — delegates to shared graph-renderer
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
  const isDeprecated = node.status === KNOWN_STATUS.DEPRECATED && !node.supersededBy;
  const isInProgress = node.status === KNOWN_STATUS.IN_PROGRESS && !node.supersededBy;
  const isRecent =
    !isSuperseded &&
    !isDeprecated &&
    Date.now() - new Date(node.updatedAt).getTime() < GraphStyle.RECENT.WINDOW_MS;

  drawNodeOrb(ctx, x, y, radius, {
    id: node.id,
    name: node.name,
    tags: node.tags,
    connections: node.connections ?? 0,
    superseded: isSuperseded,
    deprecated: isDeprecated,
    pulse: isInProgress,
  }, time);

  // Recent update ring
  if (isRecent) {
    const { ALPHA_MAX, PERIOD_MS } = GraphStyle.RECENT;
    const p = pulseValue(time, 0, ALPHA_MAX, PERIOD_MS);
    const tagColor = GraphStyle.nodeBaseColor(node);
    const r = parseInt(tagColor.slice(1, 3), 16);
    const g = parseInt(tagColor.slice(3, 5), 16);
    const b = parseInt(tagColor.slice(5, 7), 16);
    const ringOuter = radius + 6;
    const ringGrad = ctx.createRadialGradient(x, y, radius, x, y, ringOuter);
    ringGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${p})`);
    ringGrad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.beginPath();
    ctx.arc(x, y, ringOuter, 0, 2 * Math.PI);
    ctx.fillStyle = ringGrad;
    ctx.fill();
  }

  // Search-match breathing ring
  if (isSearchMatch) {
    const { ALPHA_MIN, ALPHA_MAX, PERIOD_MS } = GraphStyle.SEARCH;
    const p = pulseValue(time, ALPHA_MIN, ALPHA_MAX, PERIOD_MS);
    const tagColor = GraphStyle.nodeBaseColor(node);
    const r = parseInt(tagColor.slice(1, 3), 16);
    const g = parseInt(tagColor.slice(3, 5), 16);
    const b = parseInt(tagColor.slice(5, 7), 16);
    const ringOuter = radius + 6;
    const ringGrad = ctx.createRadialGradient(x, y, radius, x, y, ringOuter);
    ringGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${p})`);
    ringGrad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.beginPath();
    ctx.arc(x, y, ringOuter, 0, 2 * Math.PI);
    ctx.fillStyle = ringGrad;
    ctx.fill();
  }

  // Highlight ring (selected / hovered)
  if (isHighlighted && !isSearchMatch) {
    ctx.beginPath();
    ctx.arc(x, y, radius + 4, 0, 2 * Math.PI);
    ctx.strokeStyle = GraphStyle.HIGHLIGHT.COLOR;
    ctx.lineWidth = GraphStyle.HIGHLIGHT.WIDTH / globalScale;
    ctx.stroke();
  }

  // Label
  if (globalScale > GraphStyle.LABEL.SCALE_THRESHOLD) {
    drawNodeLabel(ctx, x, y, radius, node.name, isSuperseded, GraphStyle.LABEL.MAX_CHARS, globalScale);
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MemoryGraphClient({ graphData }: MemoryGraphClientProps) {
  const [localGraph, setLocalGraph] = useState(graphData);
  const [tagFilter, setTagFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNodeFG | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const graphContainerRef = useRef<HTMLDivElement>(null);
  const animTimeRef = useRef(0);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const handleNodeUpdated = useCallback((updated: GraphNode) => {
    setLocalGraph((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) => (n.id === updated.id ? updated : n)),
    }));
  }, []);

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
    localGraph.nodes.forEach((n) => n.tags.forEach((t) => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [localGraph.nodes]);

  // ---- Filters ----
  const filteredData = useMemo(() => {
    let nodes = localGraph.nodes;

    if (tagFilter) {
      nodes = nodes.filter((n) =>
        n.tags.some((t) => t.toLowerCase().includes(tagFilter.toLowerCase())),
      );
    }

    const nodeIds = new Set(nodes.map((n) => n.id));
    const getId = (ref: string | { id: string }) =>
      typeof ref === "string" ? ref : ref.id;
    const links = localGraph.links.filter((l) => {
      return nodeIds.has(getId(l.source)) && nodeIds.has(getId(l.target));
    });

    return { nodes, links };
  }, [localGraph, tagFilter]);

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
    const getId = (ref: string | { id: string }) =>
      typeof ref === "string" ? ref : ref.id;
    const ids = new Set<string>();
    localGraph.links.forEach((link) => {
      if (getId(link.source) === selectedNodeId) ids.add(getId(link.target));
      if (getId(link.target) === selectedNodeId) ids.add(getId(link.source));
    });
    return Array.from(ids);
  }, [selectedNodeId, localGraph.links]);

  // ---- Node lookup map for force-graph callbacks ----
  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNodeFG>();
    filteredData.nodes.forEach((n) => {
      map.set(n.id, n);
    });
    return map;
  }, [filteredData.nodes]);

  const selectedNode = useMemo(
    () => (selectedNodeId ? nodeMap.get(selectedNodeId) ?? null : null),
    [nodeMap, selectedNodeId],
  );

  // ---- Handlers ----
  const handleNodeClick = useCallback((node: NodeObject) => {
    const id = typeof node.id === "string" ? node.id : String(node.id ?? "");
    setSelectedNodeId(id);
  }, []);

  const handleNodeHover = useCallback(
    (node: NodeObject | null) => {
      if (!node) {
        setHoveredNode(null);
        return;
      }
      const id = typeof node.id === "string" ? node.id : String(node.id ?? "");
      setHoveredNode(nodeMap.get(id) ?? null);
    },
    [nodeMap],
  );

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
      const id = typeof node.id === "string" ? node.id : String(node.id ?? "");
      const gNode = nodeMap.get(id);
      if (!gNode) return;
      const isSelected = gNode.id === selectedNodeId;
      const isHovered = gNode.id === hoveredNode?.id;
      const isSearch = searchHighlightIds.size > 0 && searchHighlightIds.has(gNode.id);
      const isHighlighted = isSelected || isHovered;
      renderNode(gNode, ctx, globalScale, isHighlighted, isSearch, animTimeRef.current);
    },
    [nodeMap, selectedNodeId, hoveredNode, searchHighlightIds],
  );

  // ---- Helpers for link endpoint IDs ----
  const supersedesLinkPairs = useMemo(() => {
    const set = new Set<string>();
    filteredData.links.forEach((link) => {
      if (link.type === "supersedes") {
        set.add(`${link.source}|||${link.target}`);
      }
    });
    return set;
  }, [filteredData.links]);

  function linkEndpointId(endpoint: string | number | NodeObject | undefined): string {
    if (typeof endpoint === "object" && endpoint !== null && "id" in endpoint) {
      return String(endpoint.id ?? "");
    }
    return String(endpoint ?? "");
  }

  // ---- Canvas link rendering ----
  const isSupersedes = useCallback(
    (link: LinkObject) => {
      const key = `${linkEndpointId(link.source)}|||${linkEndpointId(link.target)}`;
      return supersedesLinkPairs.has(key);
    },
    [supersedesLinkPairs],
  );

  const linkColor = useCallback(
    (link: LinkObject) =>
      isSupersedes(link) ? GraphStyle.LINK.COLOR_SUPERSEDES : GraphStyle.LINK.COLOR_RELATED,
    [isSupersedes],
  );

  const linkWidth = useCallback(
    (link: LinkObject) =>
      isSupersedes(link) ? GraphStyle.LINK.WIDTH_SUPERSEDES : GraphStyle.LINK.WIDTH_RELATED,
    [isSupersedes],
  );

  const linkDirectionalParticles = useCallback(
    (link: LinkObject) => (isSupersedes(link) ? GraphStyle.LINK.SUPERSEDES_PARTICLE_COUNT : 0),
    [isSupersedes],
  );

  const linkDirectionalParticleSpeed = useCallback(
    (link: LinkObject) => (isSupersedes(link) ? GraphStyle.LINK.SUPERSEDES_PARTICLE_SPEED : 0),
    [isSupersedes],
  );

  const linkDirectionalParticleWidth = useCallback(
    (link: LinkObject) => (isSupersedes(link) ? GraphStyle.LINK.SUPERSEDES_PARTICLE_WIDTH : 0),
    [isSupersedes],
  );

  const linkDirectionalParticleColor = useCallback(() => GraphStyle.LINK.COLOR_SUPERSEDES, []);

  return (
    <div className="flex flex-1 flex-col">
      <div className="sticky top-10 bg-canon-bg z-40 -mx-5 px-5">
        <GraphFilters
          tagFilter={tagFilter}
          onTagChange={setTagFilter}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          allTags={allTags}
          nodeCount={filteredData.nodes.length}
          linkCount={filteredData.links.length}
        />
      </div>

      <div className="flex min-h-0 flex-1">
        <div
          ref={graphContainerRef}
          className={`relative min-h-0 bg-canon-bg ${selectedNode ? "w-[65%]" : "w-full"}`}
          style={{
            backgroundImage: `
              radial-gradient(circle, ${GraphStyle.GRID.DOT_COLOR} ${GraphStyle.GRID.DOT_RADIUS}px, transparent ${GraphStyle.GRID.DOT_RADIUS}px)
            `,
            backgroundSize: `${GraphStyle.GRID.SPACING}px ${GraphStyle.GRID.SPACING}px`,
          }}
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
            backgroundColor="rgba(0,0,0,0)"
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
              allNodes={localGraph.nodes}
              connectedNodeIds={connectedNodeIds}
              onClose={() => setSelectedNodeId(null)}
              onSelectNode={setSelectedNodeId}
              onNodeUpdated={handleNodeUpdated}
            />
          </div>
        )}
      </div>
    </div>
  );
}
