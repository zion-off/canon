"""Shared embedding utilities for Canon function tools.

Provides a single abstraction for generating embeddings and building
retrieval-optimized text from memory node documents, eliminating
duplicate embed() error handling and cross-tool imports.
"""

from __future__ import annotations

import logging

from src.agent.agent_platform import CanonModel
from src.agent.models import CanonizeError, HybridSearchError

logger = logging.getLogger(__name__)


def build_embedding_text(doc: object) -> str:
    """Build a retrieval-optimized semantic representation of a memory node."""
    from src.agent.models import MemoryNodeInput

    if not isinstance(doc, MemoryNodeInput):
        lines: list[str] = []
        if isinstance(doc, dict):
            header = doc.get("name", "")
            if doc.get("status"):
                header += f" [{doc['status']}]"
            lines.append(header)
            if doc.get("description"):
                lines.append(str(doc["description"]))
            if doc.get("content"):
                lines.append(str(doc["content"])[:1500])
            if doc.get("tags"):
                lines.append("Tags: " + ", ".join(doc["tags"]))
        return "\n".join(filter(None, lines))

    lines: list[str] = []
    header = doc.name
    if doc.status:
        header += f" [{doc.status}]"
    lines.append(header)
    if doc.description:
        lines.append(doc.description)
    if doc.content:
        lines.append(doc.content[:1500])
    if doc.tags:
        lines.append("Tags: " + ", ".join(doc.tags))
    return "\n".join(filter(None, lines))


async def generate_embedding(
    text: str,
    task_type: str,
    model: str,
    *,
    context_label: str = "embedding",
) -> list[float]:
    """Generate an embedding vector with consistent error handling.

    Args:
        text: The text to embed.
        task_type: Gemini embedding task type (e.g. "RETRIEVAL_DOCUMENT").
        model: The embedding model name.
        context_label: Human label for log/error messages (e.g. "hybrid_search").

    Returns:
        The embedding vector as a list of floats.

    Raises:
        HybridSearchError: If embedding generation fails.
    """
    try:
        return await CanonModel.embed(text, task_type=task_type, model=model)
    except Exception as exc:
        logger.warning("%s: embedding failed | error=%s", context_label, exc)
        raise EmbeddingError(
            error=f"Embedding generation failed: {exc}",
            hint="Embedding model unavailable",
            retry="Wait and retry. If persistent, surface the error.",
        ) from exc


class EmbeddingError(Exception):
    """Structured embedding failure, convertible to tool-specific error types."""

    def __init__(self, error: str, hint: str, retry: str) -> None:
        super().__init__(error)
        self.error = error
        self.hint = hint
        self.retry = retry

    def as_hybrid_search_error(self) -> HybridSearchError:
        return HybridSearchError(error=self.error, hint=self.hint, retry=self.retry)

    def as_canonize_error(self) -> CanonizeError:
        return CanonizeError(error=self.error, hint=self.hint, retry=self.retry)
