"""MCP CallToolResult response parsing utilities.

Extracts structured data and error information from the raw results
returned by mongodb-mcp-server tool calls.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_UNTRUSTED_CONTENT_RE = re.compile(
    r"<untrusted-user-data-[^>]+>(.*?)</untrusted-user-data-[^>]+>",
    re.DOTALL,
)


def mcp_result_is_error(result: Any) -> bool:
    """Check whether an MCP CallToolResult indicates an error.

    Uses defensive getattr to handle response objects that may or
    may not carry an isError flag.
    """
    return bool(getattr(result, "isError", False))


def extract_mcp_error_text(result: Any) -> str:
    """Extract the first text content from a failed MCP CallToolResult.

    Returns the first non-empty text string found in result.content,
    or an empty string if nothing is extractable.
    """
    for item in getattr(result, "content", []):
        text = getattr(item, "text", "")
        if text:
            return str(text)
    return ""


def parse_mcp_docs(content_items: list[Any]) -> list[dict[str, Any]]:
    """Extract documents from MCP CallToolResult content items.

    Handles TextContent with optional <untrusted-user-data> wrappers
    produced by the mongodb-mcp-server. Returns a flat list of dicts.
    """
    docs: list[dict[str, Any]] = []
    for item in content_items:
        raw = getattr(item, "text", "")
        if not raw:
            continue

        parsed = False
        for inner in _UNTRUSTED_CONTENT_RE.findall(raw):
            candidate = inner.strip()
            if not candidate:
                continue
            try:
                parsed_data = json.loads(candidate)
                docs.extend(parsed_data) if isinstance(
                    parsed_data, list
                ) else docs.append(parsed_data)
                parsed = True
                break
            except json.JSONDecodeError:
                pass
        if parsed:
            continue

        try:
            parsed_data = json.loads(raw)
            docs.extend(parsed_data) if isinstance(parsed_data, list) else docs.append(
                parsed_data
            )
        except json.JSONDecodeError:
            logger.debug(
                "parse_mcp_docs: skipping non-JSON content | raw=%.120s", raw[:120]
            )
    return docs
