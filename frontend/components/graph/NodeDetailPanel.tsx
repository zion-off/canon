"use client";

import type { GraphNode } from "@/lib/schemas/graph";

interface NodeDetailPanelProps {
  node: GraphNode;
  allNodes: GraphNode[];
  connectedNodeIds: string[];
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
}

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    active: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    in_progress: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    deprecated: "bg-gray-500/20 text-gray-400 border-gray-500/30",
    resolved: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    completed: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  };

  const classes =
    colorMap[status] ?? "bg-slate-500/20 text-slate-400 border-slate-500/30";

  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${classes}`}
    >
      {status.replace("_", " ")}
    </span>
  );
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
    <aside className="flex h-full w-full flex-col overflow-y-auto border-l border-white/[0.08] bg-[#0f0f1a]">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-white/[0.08] p-4">
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-[Syne,sans-serif] text-lg font-semibold text-slate-200">
            {node.name}
          </h2>
          <div className="mt-1.5">
            <StatusBadge status={node.status} />
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-2 shrink-0 rounded p-1 text-slate-400 hover:bg-white/[0.05] hover:text-slate-200"
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
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
              Tags
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {node.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-white/[0.08] bg-white/[0.03] px-2 py-0.5 text-xs text-slate-400"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Description */}
        <div>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            Description
          </h3>
          <p className="text-sm leading-relaxed text-slate-300">
            {node.description || "No description available."}
          </p>
        </div>

        {/* Connected nodes */}
        {connectedNodes.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
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
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
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
              <span className="text-sm text-slate-500">—</span>
            )}
          </div>
          <div>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
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
              <span className="text-sm text-slate-500">—</span>
            )}
          </div>
        </div>

        {/* Dates */}
        <div className="border-t border-white/[0.08] pt-4">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-slate-500">Created</span>
              <p className="mt-0.5 text-slate-300">
                {formatDate(node.createdAt)}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Updated</span>
              <p className="mt-0.5 text-slate-300">
                {formatDate(node.updatedAt)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
