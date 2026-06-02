"""Insert seed nodes into MongoDB.

Reads seed_data/nodes.json and inserts all nodes into the canon database.
Idempotent: deletes existing seed nodes by their pre-known IDs before inserting.

Usage:
    cd backend/scripts/seed && uv run insert_seed.py
"""

import json
from pathlib import Path

from bson import ObjectId
from node_definitions import TENANT_ID
from pymongo import MongoClient

SEED_DATA_DIR = Path(__file__).parent / "seed_data"
NODES_FILE = SEED_DATA_DIR / "nodes.json"

MONGODB_URI = "mongodb://localhost:27117/?directConnection=true"
DATABASE_NAME = "canon"
COLLECTION_NAME = "memory_nodes"


def ejson_to_bson(doc):
    """Convert EJSON {$oid: ...} to BSON ObjectId recursively."""
    if isinstance(doc, dict):
        if "$oid" in doc:
            return ObjectId(doc["$oid"])
        return {k: ejson_to_bson(v) for k, v in doc.items()}
    if isinstance(doc, list):
        return [ejson_to_bson(item) for item in doc]
    return doc


def main():
    if not NODES_FILE.exists():
        print(f"ERROR: {NODES_FILE} not found. Run generate_seed.py first.")
        return

    print(f"Reading {NODES_FILE}...")
    with open(NODES_FILE) as f:
        documents = json.load(f)

    print(f"Connecting to {MONGODB_URI}...")
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    # Inject tenant ID into all documents
    tenant_id = ObjectId(TENANT_ID)
    for doc in documents:
        doc["tenantId"] = {"$oid": TENANT_ID}

    # Extract seed node IDs for idempotent cleanup
    seed_ids = [ObjectId(doc["_id"]["$oid"]) for doc in documents]

    print("Deleting existing seed nodes...")
    result = collection.delete_many({"_id": {"$in": seed_ids}})
    if result.deleted_count > 0:
        print(f"  Deleted {result.deleted_count} existing nodes")

    print(f"Inserting {len(documents)} nodes...")
    bson_docs = [ejson_to_bson(doc) for doc in documents]
    result = collection.insert_many(bson_docs)
    print(f"  Inserted {len(result.inserted_ids)} nodes")

    print("Wiring bidirectional relationships...")
    relationship_count = 0
    for doc in documents:
        source_id = ObjectId(doc["_id"]["$oid"])
        for related in doc.get("relatedEntityIds", []):
            target_id = ObjectId(related["$oid"])
            collection.update_one(
                {"_id": target_id, "tenantId": tenant_id},
                {"$addToSet": {"relatedEntityIds": source_id}},
            )
            relationship_count += 1

    print(f"  Wired {relationship_count} relationships")
    print("\n✓ Seed data inserted successfully")


if __name__ == "__main__":
    main()
