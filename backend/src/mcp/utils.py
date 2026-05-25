"""Shared utilities for the MCP agent layer."""

from typing import Any

import google.genai as genai

_genai_client: genai.Client | None = None


def get_genai_client() -> genai.Client:
    """Return a lazily-initialized Gemini API client singleton."""
    global _genai_client  # noqa: PLW0603
    if _genai_client is None:
        _genai_client = genai.Client()
    return _genai_client


def summarize_args(args: dict[str, Any] | None) -> str:
    """Produce a human-readable summary of tool arguments for the event feed."""
    if not args:
        return ""
    if "query" in args:
        return str(args["query"])[:100]
    if (
        "document" in args
        and isinstance(args["document"], dict)
        and "name" in args["document"]
    ):
        return f"writing: {args['document']['name']}"
    return ", ".join(f"{k}={str(v)[:50]}" for k, v in list(args.items())[:3])


def summarize_result(tool_name: str, args: dict[str, Any], result: dict) -> str:
    """Produce a concise summary of a completed tool invocation."""
    arg_hint = summarize_args(args)
    status = result.get("status", "ok")
    return f"{tool_name}({arg_hint}) -> {status}"
