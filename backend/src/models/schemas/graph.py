from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.models.schemas._base import MongoModel


class GraphNode(MongoModel):
    id: str = Field(validation_alias="_id")
    name: str
    description: str = Field(default="")
    content: str = Field(default="")
    status: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    supersedes: str | None = None
    superseded_by: str | None = Field(default=None, alias="supersededBy")
    updated_at: str = Field(default="", alias="updatedAt")
    created_at: str = Field(default="", alias="createdAt")
    connections: int = Field(default=0)


class UpdateNodeRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    content: str | None = None
    status: str | None = None
    tags: list[str] | None = None


class UpdateNodeResponse(MongoModel):
    id: str = Field(validation_alias="_id")
    name: str
    description: str = ""
    content: str = ""
    status: str = ""
    tags: list[str] = Field(default_factory=list)
    supersedes: str | None = None
    superseded_by: str | None = Field(default=None, alias="supersededBy")
    updated_at: str = Field(default="", alias="updatedAt")
    created_at: str = Field(default="", alias="createdAt")
    connections: int = Field(default=0)


class GraphLink(BaseModel):
    source: str
    target: str
    type: Literal["related", "supersedes"]


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]
