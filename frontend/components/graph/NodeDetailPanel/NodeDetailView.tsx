import type { GraphNode } from "@/lib/schemas/graph";
import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";
import { formatShortDate } from "@/lib/date-utils";

interface NodeDetailViewProps {
  node: GraphNode;
  connectedNodes: GraphNode[];
  supersedesNode: GraphNode | null;
  supersededByNode: GraphNode | null;
  onClose: () => void;
  onEdit: () => void;
  onSelectNode: (nodeId: string) => void;
}

function PencilIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M11 1.5a1.5 1.5 0 0 1 2.1 2.1L4.5 13l-2.5.5.5-2.5L11 1.5z" />
    </svg>
  );
}

export function NodeDetailView({
  node,
  connectedNodes,
  supersedesNode,
  supersededByNode,
  onClose,
  onEdit,
  onSelectNode,
}: NodeDetailViewProps) {
  return (
    <aside className="flex h-full w-full flex-col overflow-y-auto border-l border-canon-border bg-canon-surface">
      <div className="flex items-start justify-between border-b border-canon-border p-4">
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-condensed text-lg font-bold text-canon-text">{node.name}</h2>
          <div className="mt-1.5 flex items-center gap-2">
            <Badge variant={node.status as BadgeVariant}>{node.status.replace("_", " ")}</Badge>
          </div>
        </div>
        <div className="ml-2 flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={onEdit}
            className="p-1 text-canon-text-secondary hover:bg-white/5 hover:text-canon-text transition-colors"
            aria-label="Edit memory"
          >
            <PencilIcon />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-canon-text-secondary hover:bg-white/5 hover:text-canon-text transition-colors"
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
      </div>

      <div className="flex-1 space-y-5 p-4">
        {node.tags.length > 0 && (
          <div>
            <h3 className="mb-2 font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Tags
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {node.tags.map((tag) => (
                <span
                  key={tag}
                  className="border border-canon-border px-2 py-0.5 font-mono text-xs text-canon-text-secondary"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        <div>
          <h3 className="mb-2 font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
            Description
          </h3>
          <p className="text-sm leading-relaxed text-canon-text">
            {node.description || "No description available."}
          </p>
        </div>

        {connectedNodes.length > 0 && (
          <div>
            <h3 className="mb-2 font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Connected to
            </h3>
            <ul className="space-y-1">
              {connectedNodes.map((cn) => (
                <li key={cn.id}>
                  <button
                    type="button"
                    onClick={() => onSelectNode(cn.id)}
                    className="w-full px-2 py-1 text-left text-sm text-canon-accent hover:bg-white/5 transition-colors"
                  >
                    {cn.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="space-y-3">
          <div>
            <h3 className="mb-1 font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Supersedes
            </h3>
            {supersedesNode ? (
              <button
                type="button"
                onClick={() => onSelectNode(supersedesNode.id)}
                className="text-sm text-canon-accent hover:underline"
              >
                {supersedesNode.name}
              </button>
            ) : (
              <span className="text-sm text-canon-text-secondary">—</span>
            )}
          </div>
          <div>
            <h3 className="mb-1 font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Superseded by
            </h3>
            {supersededByNode ? (
              <button
                type="button"
                onClick={() => onSelectNode(supersededByNode.id)}
                className="text-sm text-canon-accent hover:underline"
              >
                {supersededByNode.name}
              </button>
            ) : (
              <span className="text-sm text-canon-text-secondary">—</span>
            )}
          </div>
        </div>

        <div className="border-t border-canon-border pt-4">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="font-condensed font-bold uppercase tracking-wider text-canon-text-secondary">
                Created
              </span>
              <p className="mt-0.5 text-canon-text">{formatShortDate(node.createdAt)}</p>
            </div>
            <div>
              <span className="font-condensed font-bold uppercase tracking-wider text-canon-text-secondary">
                Updated
              </span>
              <p className="mt-0.5 text-canon-text">{formatShortDate(node.updatedAt)}</p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
