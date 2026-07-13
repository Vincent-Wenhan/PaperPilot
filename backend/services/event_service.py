"""Event publisher backed by the durable ``EventRepository``.

The publisher is the bridge between:

* ``backend.repositories.event_repository.EventRepository`` — durable
  SQLite storage, the source of truth.
* In-process async subscribers — used by the SSE handler to push events
  to connected clients.

Publishing an event is a single logical operation:

1. Allocate the next monotonic ``sequence`` for the run.
2. Append the event to the repository.
3. Notify in-process subscribers (one queue per subscriber).
4. Also append to the legacy JSONL file so existing tooling keeps working.

Subscribers that fall behind are dropped (their queue is bounded); they
can recover from the repository on reconnect.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from backend.repositories.event_repository import (
    EventRepository,
    RunEvent,
    new_event_id,
    utc_now,
)
from backend.schemas import WorkbenchEvent

try:
    from backend.services.run_service import STORAGE_DIR
except Exception:  # pragma: no cover - run_service may not be importable yet
    STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"


class EventPublisher:
    """Persist and broadcast workbench events.

    The publisher deliberately keeps the legacy JSONL behaviour to avoid
    breaking existing tooling that reads ``events_<run_id>.jsonl``.  New
    clients should consume the SQLite-backed history via SSE.
    """

    def __init__(
        self,
        repository: EventRepository,
        storage_dir: Path | None = None,
    ) -> None:
        self._repository = repository
        self._storage_dir = storage_dir or STORAGE_DIR
        self._subscribers: dict[str, set[asyncio.Queue[RunEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._jsonl_dir = self._storage_dir
        self._jsonl_dir.mkdir(parents=True, exist_ok=True)

    @property
    def repository(self) -> EventRepository:
        return self._repository

    async def publish(
        self,
        *,
        run_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        node: str = "",
        agent: str = "",
        status: str = "",
        message: str = "",
        message_id: str | None = None,
    ) -> RunEvent:
        sequence = self._repository.next_sequence(run_id)
        event = RunEvent(
            event_id=new_event_id(),
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            node=node,
            agent=agent,
            status=status,
            message=message,
            payload=payload or {},
            created_at=utc_now().isoformat(),
        )
        if message_id:
            event.payload["message_id"] = message_id

        self._repository.append(event)
        self._append_jsonl(event)

        async with self._lock:
            queues = list(self._subscribers.get(run_id, set()))

        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Slow consumer: it will resync from the repository.
                pass

        return event

    def subscribe(
        self,
        *,
        run_id: str,
        after: int = 0,
    ) -> "EventSubscription":
        """Subscribe to events for ``run_id``.

        ``after`` is the last sequence the consumer successfully processed.
        The subscription first replays missed events from the repository,
        then streams live events.
        """

        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=256)
        subscription = EventSubscription(queue=queue, run_id=run_id, after=after)
        self._subscribers[run_id].add(queue)
        return subscription

    def unsubscribe(self, subscription: "EventSubscription") -> None:
        queues = self._subscribers.get(subscription.run_id, set())
        queues.discard(subscription.queue)

    def _append_jsonl(self, event: RunEvent) -> None:
        path = self._jsonl_dir / f"events_{event.run_id}.jsonl"
        payload = {
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
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class EventSubscription:
    """Handle representing a live subscription to a run's events."""

    def __init__(
        self,
        *,
        queue: asyncio.Queue[RunEvent],
        run_id: str,
        after: int,
    ) -> None:
        self.queue = queue
        self.run_id = run_id
        self.after = after


_event_repository: EventRepository | None = None
_event_publisher: EventPublisher | None = None


def get_event_repository() -> EventRepository:
    global _event_repository
    if _event_repository is None:
        db_path = STORAGE_DIR / "events.sqlite"
        _event_repository = EventRepository(db_path)
    return _event_repository


def get_event_publisher() -> EventPublisher:
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = EventPublisher(get_event_repository())
    return _event_publisher


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
