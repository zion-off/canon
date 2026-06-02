"""Generate seed embeddings and save to seed_data/nodes.json.

Reads node definitions, builds concise embeddingText for each, calls
Google GenAI text-embedding-004 via Vertex AI, and writes the full
MongoDB documents (EJSON format) to seed_data/nodes.json.

Usage:
    cd backend && uv run scripts/seed/generate_seed.py
"""

import json
import time
from pathlib import Path

from google import genai
from google.genai import types
from node_definitions import NODES, build_embedding_text

SEED_DATA_DIR = Path(__file__).parent / "seed_data"
OUTPUT_FILE = SEED_DATA_DIR / "nodes.json"

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSIONS = 768


def embed(client: genai.Client, text: str) -> list[float]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )
    if not response.embeddings or response.embeddings[0].values is None:
        raise RuntimeError("Embedding API returned empty response")
    return response.embeddings[0].values


def build_document(node: dict, embedding_text: str, embedding: list[float]) -> dict:
    return {
        "_id": {"$oid": node["_id"]},
        "name": node["name"],
        "description": node["description"],
        "content": node["content"],
        "status": node["status"],
        "tags": node["tags"],
        "relatedEntityIds": [{"$oid": rid} for rid in node["related_entity_ids"]],
        "embeddingText": embedding_text,
        "embedding": embedding,
        "metadata": node["metadata"],
        "createdAt": node["createdAt"],
        "updatedAt": node["updatedAt"],
    }


def main():
    print(f"Generating embeddings for {len(NODES)} nodes...\n")
    client = genai.Client(vertexai=True)
    documents = []

    for i, node in enumerate(NODES, 1):
        text = build_embedding_text(node)
        print(f"  [{i}/{len(NODES)}] {node['name']}...", end=" ", flush=True)
        embedding = embed(client, text)
        print(f"✓ ({len(embedding)} dims)")
        documents.append(build_document(node, text, embedding))
        if i < len(NODES):
            time.sleep(0.1)

    SEED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(documents, indent=2))
    print(f"\nWrote {len(documents)} nodes to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
