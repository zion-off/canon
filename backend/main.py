"""Canon backend — FastAPI application entry point.

Serves REST API routes for the frontend and the MCP proxy:
- /api/v1/auth       — authentication
- /api/v1/teams      — team management
- /api/v1/sessions   — session listing, events, SSE streaming (frontend)
- /api/v1/graph      — knowledge graph
- /api/v1/agent      — agent invocation (for MCP proxy)
- /api/v1/resources  — org-state, org-momentum (for MCP proxy)

Lifespan wires up MongoDB, AgentEventFeed, and the ADK agent subprocess.
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.error_handlers import unexpected_exception_handler
from src.lifespan import configure_logging, lifespan
from src.routers.agent import router as agent_router
from src.routers.auth import router as auth_router
from src.routers.graph import router as graph_router
from src.routers.prompts import router as prompts_router
from src.routers.resources import router as resources_router
from src.routers.sessions import router as sessions_router
from src.routers.teams import router as teams_router

configure_logging()

app = FastAPI(
    title="Canon",
    description="Organizational continuity agent for engineering teams",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, unexpected_exception_handler)

# REST API routers
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(teams_router, prefix="/api/v1/teams")
app.include_router(sessions_router, prefix="/api/v1/sessions")
app.include_router(graph_router, prefix="/api/v1/graph")
app.include_router(agent_router, prefix="/api/v1/agent")
app.include_router(resources_router, prefix="/api/v1/resources")
app.include_router(prompts_router, prefix="/api/v1/prompts")


@app.get("/health", tags=["meta"])
async def health_check(request: Request) -> dict[str, str]:
    """Readiness probe — reports degraded when agents failed to initialize."""
    agents_ready: bool = request.app.state.agents_ready
    if agents_ready:
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
