"""SSE stream consumer for the Canon backend agent."""

from __future__ import annotations

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
    QueryParam,
    SSEField,
    ToolCallStatus,
)

log = logging.getLogger(__name__)

_SSE_LINE_RE = re.compile(r"^(id|event|data):\s*(\S[^\n]*)")


async def consume_sse(
    client: httpx.AsyncClient,
    tenant_id: str,
    session_id: str,
    auth_header: str,
    fastmcp_ctx: Context,
) -> str:
    """Consume SSE events and return the final response text."""
    final_text: str = ""
    sse_url = f"{settings.canon_backend_url}{APIRoute.HARNESS_SESSION_STREAM.format(tenant_id=tenant_id, session_id=session_id)}"

    async with client.stream(
        "GET",
        sse_url,
        params={QueryParam.LAST_EVENT_ID: 0},
        headers={HttpHeader.AUTHORIZATION: auth_header},
    ) as response:
        if response.status_code != 200:
            log.error("SSE stream failed: %s", response.status_code)
            return "Error: could not connect to event stream"

        event_id: str | None = None
        data_lines: list[str] = []

        async for line in response.aiter_lines():
            if not line.strip():
                if data_lines:
                    result = await _handle_event(
                        event_id,
                        "\n".join(data_lines),
                        fastmcp_ctx,
                        client,
                        auth_header,
                    )
                    if result is not None:
                        final_text = result
                        break
                    event_id = None
                    data_lines = []
                continue

            match = _SSE_LINE_RE.match(line)
            if match is None:
                continue

            field, value = match.group(1), match.group(2)
            if field == SSEField.ID:
                event_id = value
            elif field == SSEField.DATA:
                data_lines.append(value)

    return final_text or "No response was generated."


async def _handle_event(
    event_id: str | None,
    data: str,
    fastmcp_ctx: Context,
    client: httpx.AsyncClient,
    auth_header: str,
) -> str | None:
    """Handle a single SSE event. Returns final_text if this is a final_response."""
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
            )

    elif event_type == EventType.FINAL_RESPONSE:
        return payload.get(EventPayload.PAYLOAD, {}).get(EventPayload.TEXT, "")

    return None
