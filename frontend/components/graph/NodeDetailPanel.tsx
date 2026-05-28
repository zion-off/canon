"use client";

import { useState } from "react";
import type { GraphNode, UpdateNodeRequest } from "@/lib/schemas/graph";
import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";
import { formatShortDate } from "@/lib/date-utils";
import { updateNode } from "@/lib/actions/graph";

interface NodeDetailPanelProps {
  node: GraphNode;
  allNodes: GraphNode[];
  connectedNodeIds: string[];
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
  onNodeUpdated: (updated: GraphNode) => void;
}

const EDITABLE_STATUSES = ["active", "in_progress", "resolved", "completed", "deprecated"] as const;

export function NodeDetailPanel({
  node,
  allNodes,
  connectedNodeIds,
  onClose,
  onSelectNode,
  onNodeUpdated,
}: NodeDetailPanelProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formName, setFormName] = useState(node.name);
  const [formDescription, setFormDescription] = useState(node.description);
  const [formContent, setFormContent] = useState(node.content);
  const [formStatus, setFormStatus] = useState(node.status);
  const [formTags, setFormTags] = useState(node.tags.join(", "));

  const connectedNodes = connectedNodeIds
    .map((id) => allNodes.find((n) => n.id === id))
    .filter(Boolean) as GraphNode[];

  const supersededByNode = node.supersededBy
    ? allNodes.find((n) => n.id === node.supersededBy)
    : null;

  const supersedesNode = node.supersedes ? allNodes.find((n) => n.id === node.supersedes) : null;

  const handleEdit = () => {
    setFormName(node.name);
    setFormDescription(node.description);
    setFormContent(node.content);
    setFormStatus(node.status);
    setFormTags(node.tags.join(", "));
    setError(null);
    setEditing(true);
  };

  const handleCancel = () => {
    setEditing(false);
    setError(null);
  };

  const handleSave = async () => {
    setError(null);
    setSaving(true);

    const parsedTags = formTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const payload: UpdateNodeRequest = {};
    if (formName !== node.name) payload.name = formName;
    if (formDescription !== node.description) payload.description = formDescription;
    if (formContent !== node.content) payload.content = formContent;
    if (formStatus !== node.status) payload.status = formStatus;
    if (parsedTags.join(",") !== node.tags.join(",")) payload.tags = parsedTags;

    if (Object.keys(payload).length === 0) {
      setEditing(false);
      setSaving(false);
      return;
    }

    try {
      const updated = await updateNode(node.id, payload);
      onNodeUpdated(updated);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <aside className="flex h-full w-full flex-col overflow-y-auto border-l border-canon-border bg-canon-surface">
        <div className="flex items-center justify-between border-b border-canon-border p-4">
          <h3 className="font-condensed text-lg font-bold text-canon-text">Edit Memory</h3>
          <button
            type="button"
            onClick={handleCancel}
            className="p-1 text-canon-text-secondary hover:bg-white/5 hover:text-canon-text transition-colors"
            aria-label="Cancel editing"
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

        <div className="flex-1 space-y-4 p-4">
          {error && (
            <div className="border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error}
            </div>
          )}

          <div>
            <label className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Name
            </label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              maxLength={120}
              className="w-full border border-canon-border bg-canon-bg px-3 py-1.5 text-sm text-canon-text focus:border-canon-accent focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Status
            </label>
            <select
              value={formStatus}
              onChange={(e) => setFormStatus(e.target.value)}
              className="w-full border border-canon-border bg-canon-bg px-3 py-1.5 text-sm text-canon-text focus:border-canon-accent focus:outline-none"
            >
              {EDITABLE_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Tags
            </label>
            <input
              type="text"
              value={formTags}
              onChange={(e) => setFormTags(e.target.value)}
              placeholder="Comma-separated"
              className="w-full border border-canon-border bg-canon-bg px-3 py-1.5 font-mono text-sm text-canon-text placeholder:text-canon-text-secondary focus:border-canon-accent focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Description
            </label>
            <textarea
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              rows={3}
              className="w-full border border-canon-border bg-canon-bg px-3 py-1.5 text-sm text-canon-text focus:border-canon-accent focus:outline-none resize-none"
            />
          </div>

          <div>
            <label className="mb-1 block font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              Content
            </label>
            <textarea
              value={formContent}
              onChange={(e) => setFormContent(e.target.value)}
              rows={6}
              className="w-full border border-canon-border bg-canon-bg px-3 py-1.5 text-sm text-canon-text focus:border-canon-accent focus:outline-none resize-none"
            />
          </div>

          <div className="pt-2 flex gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="flex-1 border border-canon-accent bg-canon-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-canon-accent/80 transition-colors disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={handleCancel}
              disabled={saving}
              className="flex-1 border border-canon-border px-3 py-1.5 text-sm text-canon-text-secondary hover:bg-white/5 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-full flex-col overflow-y-auto border-l border-canon-border bg-canon-surface">
      <div className="flex items-start justify-between border-b border-canon-border p-4">
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-condensed text-lg font-bold text-canon-text">{node.name}</h2>
          <div className="mt-1.5 flex items-center gap-2">
            <Badge variant={node.status as BadgeVariant}>{node.status.replace("_", " ")}</Badge>
            <button
              type="button"
              onClick={handleEdit}
              className="text-xs text-canon-text-secondary hover:text-canon-text transition-colors"
            >
              Edit
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-2 shrink-0 p-1 text-canon-text-secondary hover:bg-white/5 hover:text-canon-text transition-colors"
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
