"""Application lifespan: startup, shutdown, and logging configuration."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from rich.logging import RichHandler

from src.config import settings
from src.services.event_feed import AgentEventFeed, init_feed
from src.services.mongo import MongoProvider

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure structured logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
        force=True,
    )


async def _init_mongo(app: FastAPI) -> None:
    mongo = MongoProvider()
    await mongo.connect()
    app.state.mongo = mongo


async def _init_services(app: FastAPI) -> None:
    event_feed = AgentEventFeed()
    init_feed(event_feed)
    app.state.event_feed = event_feed


async def _init_agents(app: FastAPI) -> None:
    from src.agent.agents.orchestrator import initialize_agents
    from src.mcp.provider import startup as mcp_session_startup

    await mcp_session_startup()
    await initialize_agents()
    app.state.agents_ready = True
    logger.info("Canon ADK agents initialized")


async def _teardown_agents(app: FastAPI) -> None:
    from src.agent.agents.orchestrator import cleanup_agents
    from src.mcp.provider import shutdown as mcp_session_shutdown

    app.state.agents_ready = False
    await cleanup_agents()
    await mcp_session_shutdown()


async def _teardown_mongo(app: FastAPI) -> None:
    await app.state.mongo.disconnect()
    logger.info("MongoDB disconnected")


async def _kill_orphan_mcp_subprocesses() -> None:
    subprocess.run(
        ["pkill", "-f", "mongodb-mcp-server"],
        capture_output=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan — connect services, initialize agents, tear down."""
    app.state.agents_ready = False

    await _init_mongo(app)
    await _init_services(app)

    try:
        await _init_agents(app)
    except Exception:
        logger.exception("Agent initialization failed — agent run will error")

    yield

    with suppress(Exception):
        await _teardown_agents(app)

    await _teardown_mongo(app)

    if settings.environment == "development":
        await _kill_orphan_mcp_subprocesses()
