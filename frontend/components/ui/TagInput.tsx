"use client";

import { useState, type KeyboardEvent } from "react";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
  id?: string;
}

export function TagInput({
  value,
  onChange,
  placeholder = "Type and press Enter...",
  disabled = false,
  error = false,
  className = "",
  id,
}: TagInputProps) {
  const [input, setInput] = useState("");

  const addTag = (raw: string) => {
    const tag = raw.trim();
    if (!tag) return;
    if (value.includes(tag)) {
      setInput("");
      return;
    }
    onChange([...value, tag]);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag(input);
    }
    if (e.key === "Backspace" && !input && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  };

  const handleBlur = () => {
    if (input.trim()) {
      addTag(input);
    }
  };

  const removeTag = (tag: string) => {
    onChange(value.filter((t) => t !== tag));
  };

  return (
    <div
      className={`flex min-h-[2.25rem] flex-wrap items-center gap-1.5 border px-2 py-1 text-sm bg-canon-bg ${
        error ? "border-canon-error" : "border-canon-border"
      } ${disabled ? "opacity-50" : ""} ${className}`}
    >
      {value.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-0.5 border border-canon-border bg-canon-bg px-1.5 py-0.5 font-mono text-xs text-canon-text"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(tag)}
            disabled={disabled}
            className="ml-0.5 text-canon-text-secondary hover:text-canon-text disabled:opacity-50"
            aria-label={`Remove ${tag}`}
          >
            <svg
              width="10"
              height="10"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M4 4l8 8M12 4l-8 8" />
            </svg>
          </button>
        </span>
      ))}
      <input
        id={id}
        name={id}
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={value.length === 0 ? placeholder : ""}
        disabled={disabled}
        className="min-w-[8rem] flex-1 bg-transparent py-0.5 text-sm text-canon-text placeholder:text-canon-text-secondary focus:outline-none disabled:opacity-50"
      />
    </div>
  );
}
