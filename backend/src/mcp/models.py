"""Pydantic models for Canon MCP tool inputs, outputs, and metadata.

Replaces raw dictionaries with typed, validated models so every tool
has a clear contract and the LLM gets proper JSON schemas.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MemoryNodeInput(BaseModel):
    """The memory node fields the LLM specifies when calling prepare_embedding.

    All ID fields are plain hex strings — the EJSON wrapping happens
    in AmbientContextPlugin before the values reach the MongoDB MCP server.
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


class EmbeddingSuccess(BaseModel):
    """Successful embedding result."""

    embedding: list[float]


class EmbeddingError(BaseModel):
    """Failed embedding with a message."""

    error: str


type EmbeddingResult = EmbeddingSuccess | EmbeddingError


class RelationshipMeta(BaseModel):
    """Metadata about relationships to form after document insertion."""

    supersedes_id_str: str | None = Field(default=None)
    related_existing_id_strs: list[str] = Field(default_factory=list)


class PrepareSuccess(BaseModel):
    """Successful document preparation."""

    status: Literal["ready"] = "ready"
    document: dict[str, Any]
    meta: RelationshipMeta


class PrepareError(BaseModel):
    """Failed document preparation."""

    error: str


type PrepareResult = PrepareSuccess | PrepareError


class EmitCheckpointResult(BaseModel):
    """Result from emit_checkpoint."""

    status: Literal["emitted"] = "emitted"
    message: str
