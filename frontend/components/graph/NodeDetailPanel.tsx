"use client";

import type { GraphNode } from "@/lib/schemas/graph";
import { Badge } from "@/components/ui/Badge";

interface NodeDetailPanelProps {
  node: GraphNode;
  allNodes: GraphNode[];
  connectedNodeIds: string[];
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function NodeDetailPanel({
  node,
  allNodes,
  connectedNodeIds,
  onClose,
  onSelectNode,
}: NodeDetailPanelProps) {
  const connectedNodes = connectedNodeIds
    .map((id) => allNodes.find((n) => n.id === id))
    .filter(Boolean) as GraphNode[];

  const supersededByNode = node.supersededBy
    ? allNodes.find((n) => n.id === node.supersededBy)
    : null;

  const supersedesNode = node.supersedes
    ? allNodes.find((n) => n.id === node.supersedes)
    : null;

  return (
    <aside className="flex h-full w-full flex-col overflow-y-auto border-l border-canon-border bg-canon-surface">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-canon-border p-4">
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-syne text-lg font-semibold text-canon-text">
            {node.name}
          </h2>
          <div className="mt-1.5">
            <Badge variant={node.status}>
              {node.status.replace("_", " ")}
            </Badge>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-2 shrink-0 rounded p-1 text-canon-text-dim hover:bg-white/[0.05] hover:text-canon-text"
          aria-label="Close panel"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M4 4l8 8M12 4l-8 8" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 space-y-5 p-4">
        {/* Tags */}
        {node.tags.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-canon-muted">
              Tags
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {node.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-canon-border bg-white/[0.03] px-2 py-0.5 text-xs text-canon-text-dim"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Description */}
        <div>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-canon-muted">
            Description
          </h3>
          <p className="text-sm leading-relaxed text-canon-text">
            {node.description || "No description available."}
          </p>
        </div>

        {/* Connected nodes */}
        {connectedNodes.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-canon-muted">
              Connected to
            </h3>
            <ul className="space-y-1">
              {connectedNodes.map((cn) => (
                <li key={cn.id}>
                  <button
                    type="button"
                    onClick={() => onSelectNode(cn.id)}
                    className="w-full rounded px-2 py-1 text-left text-sm text-blue-400 hover:bg-white/[0.05]"
                  >
                    {cn.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Supersedes / Superseded by */}
        <div className="space-y-3">
          <div>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-canon-muted">
              Supersedes
            </h3>
            {supersedesNode ? (
              <button
                type="button"
                onClick={() => onSelectNode(supersedesNode.id)}
                className="text-sm text-blue-400 hover:underline"
              >
                {supersedesNode.name}
              </button>
            ) : (
              <span className="text-sm text-canon-muted">—</span>
            )}
          </div>
          <div>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-canon-muted">
              Superseded by
            </h3>
            {supersededByNode ? (
              <button
                type="button"
                onClick={() => onSelectNode(supersededByNode.id)}
                className="text-sm text-blue-400 hover:underline"
              >
                {supersededByNode.name}
              </button>
            ) : (
              <span className="text-sm text-canon-muted">—</span>
            )}
          </div>
        </div>

        {/* Dates */}
        <div className="border-t border-canon-border pt-4">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-canon-muted">Created</span>
              <p className="mt-0.5 text-canon-text">
                {formatDate(node.createdAt)}
              </p>
            </div>
            <div>
              <span className="text-canon-muted">Updated</span>
              <p className="mt-0.5 text-canon-text">
                {formatDate(node.updatedAt)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
