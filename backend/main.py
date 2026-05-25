"""Canon MCP server — main application entry point.

Composes FastAPI and FastMCP into a single ASGI application:
- FastMCP is mounted at /mcp (MCP-over-HTTP for coding harnesses)
- FastAPI REST routes are mounted at /api/v1 (frontend + harness REST)
- Lifespan wires up MongoDB, AgentEventFeed, and ADK agent subprocesses
"""

from __future__ import annotations

import contextlib
import logging
import sys

import uvicorn
from fastapi import FastAPI

import src.services.event_feed as event_feed_module
from src.mcp.server import mcp
from src.routers.auth import router as auth_router
from src.routers.graph import router as graph_router
from src.routers.sessions import harness_router
from src.routers.sessions import router as sessions_router
from src.routers.teams import router as teams_router
from src.services.event_feed import AgentEventFeed
from src.services.mongo import MongoProvider

sys.tracebacklimit = 0

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — connect services, initialize agents, tear down."""
    async with mcp.session_manager.run():
        mongo = MongoProvider()
        await mongo.connect()
        app.state.mongo = mongo

        event_feed = AgentEventFeed()
        event_feed_module._feed = event_feed
        app.state.event_feed = event_feed

        # Defer agent initialization — requires Gemini API key and ADK agents
        try:
            from src.mcp.agents import cleanup_agents, initialize_agents

            await initialize_agents()
            logger.info("Canon ADK agents initialized")
        except Exception:
            logger.exception("Agent initialization failed — MCP tool calls will error")

        yield

        try:
            from src.mcp.agents import cleanup_agents

            await cleanup_agents()
        except Exception:
            pass

        await mongo.disconnect()
        logger.info("MongoDB disconnected")


app = FastAPI(
    title="Canon",
    description="Organizational continuity agent for engineering teams",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/mcp", mcp.streamable_http_app())

# REST API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(harness_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    """Liveness probe for Cloud Run."""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
