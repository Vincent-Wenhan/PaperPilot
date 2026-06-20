"""FastAPI entry point for the PaperPilot Workbench API."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import actions, artifacts, checks, commands, files, llm, patches, runs, uploads
from backend.services.run_service import run_service

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
    try:
        for event in run_service.list_events(run_id):
            await websocket.send_json(event.model_dump(mode="json"))
            await asyncio.sleep(0.15)
        await websocket.send_json(
            {
                "run_id": run_id,
                "event_type": "stream_idle",
                "status": "pending",
                "message": "No additional events are available.",
            }
        )
    except WebSocketDisconnect:
        return
