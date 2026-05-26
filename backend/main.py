"""Canon MCP server — main application entry point.

Composes FastAPI and FastMCP into a single ASGI application:
- FastMCP is mounted at /mcp (MCP-over-HTTP for coding harnesses)
- FastAPI REST routes are mounted at /api/v1 (frontend + harness REST)
- Lifespan wires up MongoDB, AgentEventFeed, and ADK agent subprocesses
"""

from __future__ import annotations

import contextlib
import logging

from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
    force=True,
)

import atexit
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import settings
from src.mcp.server import mcp
from src.routers.auth import router as auth_router
from src.routers.graph import router as graph_router
from src.routers.sessions import harness_router
from src.routers.sessions import router as sessions_router
from src.routers.teams import router as teams_router
from src.services.event_feed import AgentEventFeed, init_feed
from src.services.mongo import MongoProvider

if settings.environment == "development":

    def _kill_orphan_mcp_subprocesses():
        os.system("pkill -f mongodb-mcp-server 2>/dev/null")

    atexit.register(_kill_orphan_mcp_subprocesses)

logger = logging.getLogger(__name__)


class _AppState:
    """Module-level singleton for application readiness flags."""

    agents_ready: bool = False


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — connect services, initialize agents, tear down."""
    async with mcp.session_manager.run():
        mongo = MongoProvider()
        await mongo.connect()
        app.state.mongo = mongo

        event_feed = AgentEventFeed()
        init_feed(event_feed)
        app.state.event_feed = event_feed

        # Defer agent initialization — requires Gemini and MongoDB MCP subprocess
        try:
            from src.mcp.agents import cleanup_agents, initialize_agents
            from src.mcp.mongo_connections import shutdown as mongo_mcp_shutdown
            from src.mcp.mongo_connections import startup as mongo_mcp_startup

            await mongo_mcp_startup()
            await initialize_agents()
            _AppState.agents_ready = True
            logger.info("Canon ADK agents initialized")
        except Exception:
            logger.exception("Agent initialization failed — MCP tool calls will error")

        yield

        try:
            from src.mcp.agents import cleanup_agents
            from src.mcp.mongo_connections import shutdown as mongo_mcp_shutdown

            _AppState.agents_ready = False
            await cleanup_agents()
            await mongo_mcp_shutdown()
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


@app.exception_handler(Exception)
async def _unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Log the full traceback and return a sanitized 500 response."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.mount("/mcp", mcp.streamable_http_app())

# REST API routers
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(teams_router, prefix="/api/v1/teams")
app.include_router(sessions_router, prefix="/api/v1/sessions")
app.include_router(harness_router, prefix="/api/v1/tenants/{tenant_id}")
app.include_router(graph_router, prefix="/api/v1/graph")


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    """Readiness probe — reports degraded when agents failed to initialize."""
    if _AppState.agents_ready:
        return {"status": "ok"}
    return {"status": "degraded", "detail": "agents not initialized"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_graceful_shutdown=5,
    )
