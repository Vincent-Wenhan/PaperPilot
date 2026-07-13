"""Server-Sent Events stream for a single run.

The endpoint serves the durable event log as an SSE stream.  Clients pass
``after=<sequence>`` (or the standard ``Last-Event-ID`` header) and the
stream replays missed events from the repository, then streams live
events as they are published.

SSE was chosen over WebSocket because the workbench only needs
server-to-client streaming; approvals and run creation continue to use
plain HTTP.  SSE also has native support for ``Last-Event-ID`` reconnection.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from backend.services.event_service import get_event_publisher

router = APIRouter(prefix="/api/runs", tags=["events"])


@router.get("/{run_id}/events/stream")
async def stream_run_events(
    run_id: str,
    request: Request,
    after: int = 0,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """Stream events for ``run_id`` as SSE.

    The stream is bounded by the client connection.  Reconnects pick up
    where the client left off via ``Last-Event-ID`` (or ``after``).
    """

    start_sequence = max(after, int(last_event_id or 0))
    publisher = get_event_publisher()

    async def iterator() -> AsyncIterator[bytes]:
        cursor = start_sequence

        # 1. Replay backlog from the repository.
        backlog = publisher.repository.list_after(
            run_id=run_id,
            after=cursor,
            limit=500,
        )
        for event in backlog:
            cursor = event.sequence
            yield _encode_sse(event)

        # 2. Subscribe to live events.
        subscription = publisher.subscribe(run_id=run_id, after=cursor)
        try:
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(
                        subscription.queue.get(),
                        timeout=15.0,
                    )
                except asyncio.TimeoutError:
                    yield b": keep-alive\n\n"
                    continue

                if event.sequence <= cursor:
                    continue
                cursor = event.sequence
                yield _encode_sse(event)
        finally:
            publisher.unsubscribe(subscription)

    return StreamingResponse(
        iterator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _encode_sse(event) -> bytes:
    data = {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "sequence": event.sequence,
        "event_type": event.event_type,
        "node": event.node,
        "agent": event.agent,
        "status": event.status,
        "message": event.message,
        "payload": event.payload,
        "created_at": event.created_at,
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type}\n"
        f"data: {payload}\n\n"
    ).encode("utf-8")
