"use client";

import { getHighlighter } from "@/lib/shiki";
import { useEffect, useState } from "react";

interface HighlightedCodeProps {
  code: string;
  lang: string;
  className?: string;
}

export function HighlightedCode({ code, lang, className }: HighlightedCodeProps) {
  const [html, setHtml] = useState<string | null>(null);

  useEffect(() => {
    getHighlighter().then((hl) => {
      const highlighted = hl.codeToHtml(code, {
        lang,
        theme: "github-dark",
      });
      setHtml(highlighted);
    });
  }, [code, lang]);

  if (!html) {
    return (
      <pre className={`overflow-x-auto whitespace-pre-wrap font-mono ${className ?? ""}`}>
        {code}
      </pre>
    );
  }

  return (
    <div
      className={`shiki-wrapper overflow-x-auto font-mono [&_pre]:!bg-transparent [&_pre]:!font-[inherit] ${className ?? ""}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
