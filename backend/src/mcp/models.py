"""Pydantic models for Canon MCP tool inputs, outputs, and metadata.

Replaces raw dictionaries with typed, validated models so every tool
has a clear contract and the LLM gets proper JSON schemas.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class MemoryNodeInput(BaseModel):
    """The memory node fields the LLM specifies when calling canonize_node.

    All ID fields are plain hex strings — ObjectId coercion happens in the tool.
    """

    name: str = Field(max_length=120, pattern=r"^[^\n\r]+$")
    description: str
    content: str
    status: Literal["active", "deprecated", "in_progress", "resolved", "completed"]
    tags: list[str] = Field(default_factory=list)
    related_entity_ids: list[str] = Field(
        default_factory=list,
        max_length=20,
        alias="relatedEntityIds",
        description="Hex-strings of existing nodes to link bidirectionally (max 20)",
    )
    supersedes: str | None = Field(
        default=None,
        description="Hex-string of the node this one replaces",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResultItem(BaseModel):
    """A single result from hybrid search with typed fields."""

    id: str = Field(alias="_id", description="Node ObjectId hex string")
    name: str
    description: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", mode="before")
    @classmethod
    def unwrap_oid(cls, v: Any) -> str:
        """Handle EJSON {"$oid": "hex"} from MongoDB MCP."""
        if isinstance(v, dict) and "$oid" in v:
            return v["$oid"]
        return str(v)


class HybridSearchSuccess(BaseModel):
    """Successful hybrid search with results."""

    results: list[SearchResultItem]
    count: int
    query: str
    note: str | None = None
    next_actions: list[str] = Field(default_factory=list)


class HybridSearchError(BaseModel):
    """Failed hybrid search."""

    error: str
    hint: str = ""
    retry: str | None = None


type HybridSearchResult = HybridSearchSuccess | HybridSearchError


class CanonizeSuccess(BaseModel):
    """Successful memory node persistence."""

    status: Literal["written"] = "written"
    node_id: str
    name: str
    relationships_formed: int
    note: str = "Remembered with bidirectional relationship wiring"
    next_actions: list[str] = Field(
        default_factory=lambda: [
            "Verify connectivity by tracing relationships from the new memory",
        ]
    )


class CanonizeError(BaseModel):
    """Failed memory node persistence."""

    error: str
    hint: str = ""
    retry: str | None = None


type CanonizeResult = CanonizeSuccess | CanonizeError
