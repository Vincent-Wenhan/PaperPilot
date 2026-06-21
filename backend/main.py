"""FastAPI entry point for the PaperPilot Workbench API."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import actions, artifacts, checks, commands, files, llm, patches, runs, uploads
from backend.schemas import WorkbenchEvent
from backend.services.event_service import event_service

app = FastAPI(
    title="PaperPilot Workbench API",
    version="0.1.0",
    description="API facade for the Research Agent IDE workbench.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)
app.include_router(actions.router)
app.include_router(artifacts.router)
app.include_router(checks.router)
app.include_router(commands.router)
app.include_router(files.router)
app.include_router(patches.router)
app.include_router(llm.router)
app.include_router(uploads.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "paperpilot-workbench-api"}


@app.websocket("/ws/runs/{run_id}")
async def run_event_stream(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[WorkbenchEvent] = asyncio.Queue()
    seen_event_ids: set[str] = set()

    def on_event(event: WorkbenchEvent) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    event_service.subscribe(run_id, on_event)
    try:
        for event in event_service.list_events(run_id):
            seen_event_ids.add(event.event_id)
            await websocket.send_json(event.model_dump(mode="json"))

        while True:
            event = await queue.get()
            if event.event_id in seen_event_ids:
                continue
            seen_event_ids.add(event.event_id)
            await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        return
    finally:
        event_service.unsubscribe(run_id, on_event)
