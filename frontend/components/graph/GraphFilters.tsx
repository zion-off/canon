"use client";

import { useCallback, useRef, useState } from "react";

interface GraphFiltersProps {
  tagFilter: string;
  onTagChange: (v: string) => void;
  searchQuery: string;
  onSearchChange: (v: string) => void;
  allTags: string[];
  nodeCount: number;
  linkCount: number;
}

const inputBase =
  "bg-transparent border-b border-canon-border py-1.5 font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text placeholder:text-canon-text-secondary outline-none focus:border-canon-accent transition-colors";

export function GraphFilters({
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
    <div className="flex items-center gap-3 border-b border-canon-border py-3">
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
          className={`w-40 ${inputBase}`}
        />
        {showTagSuggestions && filteredTags.length > 0 && (
          <ul className="absolute top-full left-0 z-50 mt-px max-h-48 w-full overflow-y-auto border border-canon-border bg-canon-surface-raised py-1">
            {filteredTags.slice(0, 10).map((tag) => (
              <li key={tag}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handleTagSelect(tag)}
                  className="w-full px-3 py-1 text-left text-sm text-canon-text hover:bg-white/5"
                >
                  {tag}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <input
        type="text"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search nodes…"
        className={`w-48 ${inputBase}`}
      />

      <span className="ml-auto font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
        {nodeCount} memories · {linkCount} connections
      </span>
    </div>
  );
}
