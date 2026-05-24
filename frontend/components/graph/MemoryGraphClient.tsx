"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { NodeObject, LinkObject } from "react-force-graph-2d";
import type { GraphNode, GraphLink } from "@/lib/schemas/graph";
import { STATUS } from "@/lib/constants";
import { GraphFilters } from "./GraphFilters";
import { NodeDetailPanel } from "./NodeDetailPanel";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

// Extended types for D3 simulation
type GraphNodeFG = GraphNode & NodeObject & { x?: number; y?: number };
type GraphLinkFG = GraphLink & LinkObject;

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface MemoryGraphClientProps {
  graphData: GraphData;
}

function statusColor(status: string, supersededBy: string | null): string {
  if (supersededBy) return "#9CA3AF";
  switch (status) {
    case STATUS.ACTIVE:
      return "#3B82F6";
    case STATUS.IN_PROGRESS:
      return "#F59E0B";
    case STATUS.DEPRECATED:
      return "#9CA3AF";
    case STATUS.RESOLVED:
    case STATUS.COMPLETED:
      return "#10B981";
    default:
      return "#64748B";
  }
}

function renderNode(
  node: GraphNodeFG,
  ctx: CanvasRenderingContext2D,
  globalScale: number,
  isHighlighted: boolean,
): void {
  const isRecent = Date.now() - new Date(node.updatedAt).getTime() < 7 * 86400000;
  const radius = Math.sqrt((node.connections ?? 0) + 1) * 4;
  const x = node.x ?? 0;
  const y = node.y ?? 0;

  // Highlight ring for selected/hovered
  if (isHighlighted) {
    ctx.beginPath();
    ctx.arc(x, y, radius + 4, 0, 2 * Math.PI);
    ctx.strokeStyle = "rgba(59, 130, 246, 0.6)";
    ctx.lineWidth = 2 / globalScale;
    ctx.stroke();
  }

  // Recent glow
  if (isRecent) {
    ctx.beginPath();
    ctx.arc(x, y, radius + 3, 0, 2 * Math.PI);
    ctx.fillStyle = "rgba(59, 130, 246, 0.15)";
    ctx.fill();
  }

  // Main circle
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, 2 * Math.PI);
  ctx.fillStyle = statusColor(node.status, node.supersededBy);
  ctx.fill();

  // Label (only when zoomed in enough)
  if (globalScale > 0.7) {
    const label = node.name.slice(0, 30);
    ctx.font = `${11 / globalScale}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = "rgba(226, 232, 240, 0.85)";
    ctx.fillText(label, x, y + radius + 2 / globalScale);
  }
}

export function MemoryGraphClient({ graphData }: MemoryGraphClientProps) {
  const [statusFilter, setStatusFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNodeFG | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const graphContainerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

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

  // Compute all unique tags for filter autocomplete
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    graphData.nodes.forEach((n) => n.tags.forEach((t) => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [graphData.nodes]);

  // Apply filters
  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;

    if (statusFilter) {
      nodes = nodes.filter((n) => n.status === statusFilter);
    }
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
  }, [graphData, statusFilter, tagFilter]);

  // Search highlight set
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

  // Get connected node IDs for selected node
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

  const handleNodeClick = useCallback((node: NodeObject) => {
    const gNode = node as GraphNodeFG;
    setSelectedNodeId(gNode.id);
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

  const nodeCanvasObject = useCallback(
    (node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const gNode = node as GraphNodeFG;
      const isHighlighted =
        gNode.id === selectedNodeId ||
        gNode.id === hoveredNode?.id ||
        (searchHighlightIds.size > 0 && searchHighlightIds.has(gNode.id));
      renderNode(gNode, ctx, globalScale, isHighlighted);
    },
    [selectedNodeId, hoveredNode, searchHighlightIds],
  );

  const linkColor = useCallback((link: LinkObject) => {
    const gLink = link as GraphLinkFG;
    return gLink.type === "supersedes" ? "rgba(156, 163, 175, 0.4)" : "rgba(100, 116, 139, 0.25)";
  }, []);

  const linkDirectionalArrowLength = useCallback((link: LinkObject) => {
    return (link as GraphLinkFG).type === "supersedes" ? 6 : 0;
  }, []);

  const linkWidth = useCallback((link: LinkObject) => {
    return (link as GraphLinkFG).type === "supersedes" ? 1 : 0.5;
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Filters */}
      <GraphFilters
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
        tagFilter={tagFilter}
        onTagChange={setTagFilter}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        allTags={allTags}
        nodeCount={filteredData.nodes.length}
        linkCount={filteredData.links.length}
      />

      {/* Graph + Detail panel */}
      <div className="flex min-h-0 flex-1">
        {/* Graph container */}
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
            linkDirectionalArrowLength={linkDirectionalArrowLength}
            linkDirectionalArrowRelPos={1}
            linkLineDash={(link) => ((link as GraphLinkFG).type === "supersedes" ? [4, 2] : null)}
            linkWidth={linkWidth}
            nodeLabel=""
            width={width}
            height={height}
            backgroundColor="#080810"
            cooldownTicks={100}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
          />

          {/* Custom tooltip */}
          {hoveredNode && (
            <div
              className="pointer-events-none absolute z-50 max-w-64 rounded-md border border-canon-border bg-canon-surface px-3 py-2 shadow-lg"
              style={{
                left: tooltipPos.x + 12,
                top: tooltipPos.y - 8,
              }}
            >
              <p className="text-sm font-medium text-canon-text">{hoveredNode.name}</p>
              <p className="mt-0.5 text-xs text-canon-text-dim">
                {hoveredNode.status} · {hoveredNode.connections} connections
              </p>
              {hoveredNode.tags.length > 0 && (
                <p className="mt-1 text-xs text-canon-muted">
                  {hoveredNode.tags.slice(0, 3).join(", ")}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Detail panel */}
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
