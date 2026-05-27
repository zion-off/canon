"use client";

import Markdown from "react-markdown";
import { HighlightedCode } from "./HighlightedCode";
import type { Components } from "react-markdown";

interface MarkdownRendererProps {
  children: string;
}

const components: Partial<Components> = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className ?? "");
    const codeStr = String(children).replace(/\n$/, "");

    // Fenced code block (has language-* class)
    if (match) {
      return <HighlightedCode code={codeStr} lang={match[1]} className="text-sm" />;
    }

    // Inline code
    return (
      <code
        className="rounded bg-canon-surface px-1 py-0.5 font-mono text-[0.85em] text-canon-text"
        {...props}
      >
        {children}
      </code>
    );
  },
  p({ children, ...props }) {
    return (
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-canon-text" {...props}>
        {children}
      </p>
    );
  },
  ul({ children, ...props }) {
    return (
      <ul className="list-disc pl-5 text-sm text-canon-text space-y-1" {...props}>
        {children}
      </ul>
    );
  },
  ol({ children, ...props }) {
    return (
      <ol className="list-decimal pl-5 text-sm text-canon-text space-y-1" {...props}>
        {children}
      </ol>
    );
  },
  h1({ children, ...props }) {
    return (
      <h1
        className="font-condensed font-bold text-base uppercase tracking-wider text-canon-accent mt-3 mb-1"
        {...props}
      >
        {children}
      </h1>
    );
  },
  h2({ children, ...props }) {
    return (
      <h2
        className="font-condensed font-bold text-sm uppercase tracking-wider text-canon-accent mt-3 mb-1"
        {...props}
      >
        {children}
      </h2>
    );
  },
  h3({ children, ...props }) {
    return (
      <h3
        className="font-condensed font-bold text-sm uppercase tracking-wider text-canon-text mt-2 mb-1"
        {...props}
      >
        {children}
      </h3>
    );
  },
  blockquote({ children, ...props }) {
    return (
      <blockquote
        className="border-l-2 border-canon-border pl-3 italic text-canon-text-secondary"
        {...props}
      >
        {children}
      </blockquote>
    );
  },
};

export function MarkdownRenderer({ children }: MarkdownRendererProps) {
  return <Markdown components={components}>{children}</Markdown>;
}
