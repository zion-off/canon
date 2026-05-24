"use client";

import { useCallback, useRef, useState } from "react";
import { STATUS } from "@/lib/constants";

interface GraphFiltersProps {
  statusFilter: string;
  onStatusChange: (v: string) => void;
  tagFilter: string;
  onTagChange: (v: string) => void;
  searchQuery: string;
  onSearchChange: (v: string) => void;
  allTags: string[];
  nodeCount: number;
  linkCount: number;
}

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: STATUS.ACTIVE, label: "Active" },
  { value: STATUS.IN_PROGRESS, label: "In Progress" },
  { value: STATUS.DEPRECATED, label: "Deprecated" },
  { value: STATUS.RESOLVED, label: "Resolved" },
  { value: STATUS.COMPLETED, label: "Completed" },
] as const;

export function GraphFilters({
  statusFilter,
  onStatusChange,
  tagFilter,
  onTagChange,
  searchQuery,
  onSearchChange,
  allTags,
  nodeCount,
  linkCount,
}: GraphFiltersProps) {
  const [showTagSuggestions, setShowTagSuggestions] = useState(false);
  const tagInputRef = useRef<HTMLInputElement>(null);

  const filteredTags = allTags.filter(
    (t) => tagFilter && t.toLowerCase().includes(tagFilter.toLowerCase()),
  );

  const handleTagSelect = useCallback(
    (tag: string) => {
      onTagChange(tag);
      setShowTagSuggestions(false);
    },
    [onTagChange],
  );

  return (
    <div className="flex items-center gap-3 border-b border-canon-border px-4 py-3">
      {/* Status dropdown */}
      <select
        value={statusFilter}
        onChange={(e) => onStatusChange(e.target.value)}
        className="rounded-md border border-canon-border bg-canon-surface px-3 py-1.5 text-sm text-canon-text outline-none focus:border-canon-blue/50"
      >
        {STATUS_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Tag filter */}
      <div className="relative">
        <input
          ref={tagInputRef}
          type="text"
          value={tagFilter}
          onChange={(e) => {
            onTagChange(e.target.value);
            setShowTagSuggestions(true);
          }}
          onFocus={() => setShowTagSuggestions(true)}
          onBlur={() => setTimeout(() => setShowTagSuggestions(false), 150)}
          placeholder="Filter by tag…"
          className="w-40 rounded-md border border-canon-border bg-canon-surface px-3 py-1.5 text-sm text-canon-text placeholder:text-canon-muted outline-none focus:border-canon-blue/50"
        />
        {showTagSuggestions && filteredTags.length > 0 && (
          <ul className="absolute top-full left-0 z-50 mt-1 max-h-48 w-full overflow-y-auto rounded-md border border-canon-border bg-canon-surface py-1 shadow-lg">
            {filteredTags.slice(0, 10).map((tag) => (
              <li key={tag}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handleTagSelect(tag)}
                  className="w-full px-3 py-1 text-left text-sm text-canon-text hover:bg-white/[0.05]"
                >
                  {tag}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Search */}
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search nodes…"
        className="w-48 rounded-md border border-canon-border bg-canon-surface px-3 py-1.5 text-sm text-canon-text placeholder:text-canon-muted outline-none focus:border-canon-blue/50"
      />

      {/* Counts */}
      <span className="ml-auto text-xs text-canon-muted">
        {nodeCount} nodes · {linkCount} edges
      </span>
    </div>
  );
}
