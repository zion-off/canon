"""Pydantic models for Canon MCP tool inputs, outputs, and metadata.

Replaces raw dictionaries with typed, validated models so every tool
has a clear contract and the LLM gets proper JSON schemas.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MemoryNodeInput(BaseModel):
    """The memory node fields the LLM specifies when calling canonize_node.

    All ID fields are plain hex strings — ObjectId coercion happens in the tool.
    """

    name: str
    description: str
    content: str
    status: Literal["active", "deprecated", "in_progress", "resolved", "completed"]
    tags: list[str] = Field(default_factory=list)
    related_entity_ids: list[str] = Field(
        default_factory=list,
        alias="relatedEntityIds",
        description="Hex-strings of existing nodes to link bidirectionally",
    )
    supersedes: str | None = Field(
        default=None,
        description="Hex-string of the node this one replaces",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class HybridSearchSuccess(BaseModel):
    """Successful hybrid search with results."""

    results: list[dict[str, Any]]
    count: int
    query: str


class HybridSearchError(BaseModel):
    """Failed hybrid search."""

    error: str


type HybridSearchResult = HybridSearchSuccess | HybridSearchError


class CanonizeSuccess(BaseModel):
    """Successful memory node persistence."""

    status: Literal["written"] = "written"
    node_id: str
    name: str
    relationships_formed: int


class CanonizeError(BaseModel):
    """Failed memory node persistence."""

    error: str


type CanonizeResult = CanonizeSuccess | CanonizeError


