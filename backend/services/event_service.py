"""JSONL-based event persistence for the workbench API.

Emits events to both in-memory store (for RunService compatibility) and
a JSONL file for durable storage. Supports list and subscribe operations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from backend.schemas import WorkbenchEvent


STORAGE_DIR = Path(
    os.environ.get("PAPERPILOT_STORAGE_DIR",
                   Path(__file__).resolve().parents[1] / "storage")
)


def _ensure_storage() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class EventService:
    """Persist and query workbench events via JSONL."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        self._dir = storage_dir or STORAGE_DIR
        self._subscribers: dict[str, list[Callable[[WorkbenchEvent], None]]] = {}

    def _events_path(self, run_id: str) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        return self._dir / f"events_{run_id}.jsonl"

    def emit(self, event: WorkbenchEvent) -> WorkbenchEvent:
        path = self._events_path(event.run_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
        for cb in self._subscribers.get(event.run_id, []):
            try:
                cb(event)
            except Exception:
                pass
        return event

    def list_events(self, run_id: str, after_id: str = "") -> list[WorkbenchEvent]:
        path = self._events_path(run_id)
        if not path.is_file():
            return []
        events: list[WorkbenchEvent] = []
        skip = bool(after_id)
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = WorkbenchEvent.model_validate_json(line)
                except Exception:
                    continue
                if skip and after_id:
                    if event.event_id == after_id:
                        skip = False
                    continue
                events.append(event)
        return events

    def list_run_ids(self) -> list[str]:
        self._dir.mkdir(parents=True, exist_ok=True)
        run_ids: list[str] = []
        for path in sorted(self._dir.glob("events_*.jsonl")):
            run_id = path.stem.removeprefix("events_")
            if run_id:
                run_ids.append(run_id)
        return run_ids

    def subscribe(self, run_id: str, callback: Callable[[WorkbenchEvent], None]) -> None:
        self._subscribers.setdefault(run_id, []).append(callback)

    def unsubscribe(self, run_id: str, callback: Callable[[WorkbenchEvent], None]) -> None:
        subs = self._subscribers.get(run_id, [])
        if callback in subs:
            subs.remove(callback)


event_service = EventService()
