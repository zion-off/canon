import { createHighlighter, type Highlighter } from "shiki";

let _hl: Promise<Highlighter> | null = null;

function init(): Promise<Highlighter> {
  return createHighlighter({
    themes: ["github-dark"],
    langs: [
      "json",
      "typescript",
      "python",
      "bash",
      "js",
      "ts",
      "yaml",
      "sql",
      "shell",
      "markdown",
      "txt",
    ],
  });
}

export function getHighlighter(): Promise<Highlighter> {
  if (!_hl) {
    _hl = init();
  }
  return _hl;
}
