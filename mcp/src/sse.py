"""SSE stream consumer for the Canon backend agent."""

from __future__ import annotations

import asyncio
import json
import logging
import re

import httpx
from fastmcp import Context

from src.config import settings
from src.constants import (
    APIRoute,
    Elicit,
    EventPayload,
    EventType,
    HttpHeader,
    SSEError,
    SSEField,
    ToolCallStatus,
)

log = logging.getLogger(__name__)

_SSE_LINE_RE = re.compile(r"^(event|data):\s*(\S[^\n]*)")


async def consume_sse(
    client: httpx.AsyncClient,
    body: dict,
    auth_header: str,
    fastmcp_ctx: Context,
) -> str:
    """POST to /agent/run and consume the SSE stream, returning the final response.

    Reads until the server closes the connection (after run_completed). Progress
    events and confirmation requests are handled inline; the last seen
    final_response text is returned.
    """
    final_text: str = ""
    url = f"{settings.canon_backend_url}{APIRoute.AGENT_RUN}"

    async with client.stream(
        "POST",
        url,
        json=body,
        headers={HttpHeader.AUTHORIZATION: auth_header},
    ) as response:
        if response.status_code != 200:
            log.error("Agent run stream failed: %s", response.status_code)
            return "Error: could not connect to event stream"

        data_lines: list[str] = []

        try:
            async with asyncio.timeout(settings.sse_timeout_seconds):
                async for line in response.aiter_lines():
                    if not line.strip():
                        if data_lines:
                            result = await _handle_event(
                                "\n".join(data_lines),
                                fastmcp_ctx,
                                client,
                                auth_header,
                            )
                            if result is not None:
                                final_text = result
                            data_lines = []
                        continue

                    match = _SSE_LINE_RE.match(line)
                    if match is None:
                        continue

                    field, value = match.group(1), match.group(2)
                    if field == SSEField.DATA:
                        data_lines.append(value)
        except TimeoutError:
            log.warning(
                "SSE stream timed out after %s seconds", settings.sse_timeout_seconds
            )
            return SSEError.TIMEOUT

    return final_text or "No response was generated."


async def _handle_event(
    data: str,
    fastmcp_ctx: Context,
    client: httpx.AsyncClient,
    auth_header: str,
) -> str | None:
    """Handle a single SSE event. Returns the response text for final_response, else None."""
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None

    event_type = payload.get(EventPayload.TYPE, "")

    if event_type == EventType.REASONING_CHECKPOINT:
        msg = payload.get(EventPayload.PAYLOAD, {}).get(EventPayload.MESSAGE, "")
        if msg:
            await fastmcp_ctx.report_progress(progress=0, total=None, message=msg)

    elif event_type == EventType.TOOL_CALL_STARTED:
        tool_name = payload.get(EventPayload.PAYLOAD, {}).get(
            EventPayload.TOOL_NAME, ""
        )
        if tool_name:
            await fastmcp_ctx.report_progress(
                progress=0, total=None, message=f"Calling {tool_name}..."
            )

    elif event_type == EventType.TOOL_CALL_COMPLETED:
        tool_name = payload.get(EventPayload.PAYLOAD, {}).get(
            EventPayload.TOOL_NAME, ""
        )
        status = payload.get(EventPayload.PAYLOAD, {}).get(
            EventPayload.STATUS, ToolCallStatus.OK
        )
        if tool_name:
            await fastmcp_ctx.report_progress(
                progress=0,
                total=None,
                message=f"{tool_name} completed ({status})",
            )

    elif event_type == EventType.CONFIRMATION_REQUESTED:
        p = payload.get(EventPayload.PAYLOAD, {})
        confirmation_id = p[EventPayload.CONFIRMATION_ID]

        try:
            result = await fastmcp_ctx.elicit(
                message=p[EventPayload.MESSAGE],
                response_type=p[EventPayload.OPTIONS],
                response_title=p.get(EventPayload.TITLE),
                response_description=p.get(EventPayload.DESCRIPTION),
            )
            accepted = (
                result.action == Elicit.ACCEPT_ACTION
                and result.data != Elicit.DEFAULT_REJECT
            )
        except Exception:
            log.exception("elicit failed, defaulting to accept")
            accepted = True

        if confirmation_id:
            await client.post(
                f"{settings.canon_backend_url}{APIRoute.CONFIRM.format(confirmation_id=confirmation_id)}",
                json={EventPayload.ACCEPTED: accepted},
                headers={HttpHeader.AUTHORIZATION: auth_header},
            )

    elif event_type == EventType.FINAL_RESPONSE:
        return payload.get(EventPayload.PAYLOAD, {}).get(EventPayload.TEXT, "")

    return None
