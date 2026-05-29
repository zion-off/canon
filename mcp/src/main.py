"""Canon MCP proxy — connects coding assistants to the Canon backend via stdio.

Usage:
    CANON_API_TOKEN=ct_... CANON_BACKEND_URL=https://api.example.com canon-mcp
"""

import sys
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

from src.config import settings
from src.instructions import INSTRUCTIONS

_COMPONENTS_DIR = Path(__file__).parent / "components"

mcp = FastMCP(
    "canon",
    instructions=INSTRUCTIONS,
    providers=[FileSystemProvider(_COMPONENTS_DIR)],
)


def main():
    if not settings.canon_api_token:
        print("FATAL: CANON_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
