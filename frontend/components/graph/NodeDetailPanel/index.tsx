"use client";

import { useState } from "react";
import type { GraphNode, UpdateNodeRequest } from "@/lib/schemas/graph";
import { updateNode } from "@/lib/actions/graph";
import { NodeDetailView } from "./NodeDetailView";
import { NodeDetailEdit } from "./NodeDetailEdit";

interface NodeDetailPanelProps {
  node: GraphNode;
  allNodes: GraphNode[];
  connectedNodeIds: string[];
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
  onNodeUpdated: (updated: GraphNode) => void;
}

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

  const connectedNodes = connectedNodeIds
    .map((id) => allNodes.find((n) => n.id === id))
    .filter(Boolean) as GraphNode[];

  const supersededByNode = node.supersededBy
    ? (allNodes.find((n) => n.id === node.supersededBy) ?? null)
    : null;

  const supersedesNode = node.supersedes
    ? (allNodes.find((n) => n.id === node.supersedes) ?? null)
    : null;

  const handleEdit = () => {
    setError(null);
    setEditing(true);
  };

  const handleSave = async (data: {
    name: string;
    description: string;
    content: string;
    status: string;
    tags: string[];
  }) => {
    setError(null);
    setSaving(true);

    const payload: UpdateNodeRequest = {};
    if (data.name !== node.name) payload.name = data.name;
    if (data.description !== node.description) payload.description = data.description;
    if (data.content !== node.content) payload.content = data.content;
    if (data.status !== node.status) payload.status = data.status;
    if (data.tags.join(",") !== node.tags.join(",")) payload.tags = data.tags;

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
      <NodeDetailEdit
        initialName={node.name}
        initialDescription={node.description}
        initialContent={node.content}
        initialStatus={node.status}
        initialTags={node.tags}
        saving={saving}
        error={error}
        onSave={handleSave}
        onCancel={() => {
          setEditing(false);
          setError(null);
        }}
      />
    );
  }

  return (
    <NodeDetailView
      node={node}
      connectedNodes={connectedNodes}
      supersedesNode={supersedesNode}
      supersededByNode={supersededByNode}
      onClose={onClose}
      onEdit={handleEdit}
      onSelectNode={onSelectNode}
    />
  );
}
