"""Clear agent_events, sessions, and memory_nodes collections, then show tenant ID."""

from insert_seed import DATABASE_NAME, MONGODB_URI
from pymongo import MongoClient


def main():
    print(f"Connecting to {MONGODB_URI}...")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)

    try:
        client.admin.command("ping")
        print("✓ Connected to MongoDB\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    db = client[DATABASE_NAME]

    # Clear agent_events
    result = db.agent_events.delete_many({})
    print(f"Cleared agent_events: {result.deleted_count} documents")

    # Clear sessions
    result = db.sessions.delete_many({})
    print(f"Cleared sessions: {result.deleted_count} documents")

    # Clear memory_nodes
    result = db.memory_nodes.delete_many({})
    print(f"Cleared memory_nodes: {result.deleted_count} documents")

    # Get tenant ID
    print("\nTenants:")
    for tenant in db.tenants.find({}, {"_id": 1, "name": 1, "slug": 1}):
        print(f"  {tenant['_id']} - {tenant['name']} ({tenant['slug']})")

    print("\nMemory nodes remaining:")
    count = db.memory_nodes.count_documents({})
    print(f"  {count} nodes")


if __name__ == "__main__":
    main()
