"""Event bus: persists every event and fans it out to WebSocket subscribers.

The vision pipeline runs in a worker thread; FastAPI runs on an asyncio loop. publish() is
safe to call from either side.
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime
from typing import Any

from .db import db
from .models import Event


def serialize(ev: Event) -> dict[str, Any]:
    return {
        "id": ev.id,
        "ts": ev.ts.isoformat(),
        "kind": ev.kind,
        "type": ev.type,
        "severity": ev.severity,
        "message": ev.message,
        "session_id": ev.session_id,
        "student_id": ev.student_id,
        "snapshot": f"/snapshots/{ev.snapshot}" if ev.snapshot else None,
        "payload": json.loads(ev.payload or "{}"),
        "acknowledged": ev.acknowledged,
    }


class EventBus:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subs: set[asyncio.Queue] = set()
        self._lock = threading.Lock()

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs.discard(q)

    def publish(
        self,
        *,
        kind: str,
        type: str,
        message: str,
        severity: str = "info",
        session_id: int | None = None,
        student_id: int | None = None,
        snapshot: str | None = None,
        payload: dict[str, Any] | None = None,
        ts: datetime | None = None,
    ) -> dict[str, Any]:
        ev = Event(
            kind=kind,
            type=type,
            severity=severity,
            message=message,
            session_id=session_id,
            student_id=student_id,
            snapshot=snapshot,
            payload=json.dumps(payload or {}),
        )
        if ts is not None:
            ev.ts = ts
        with db() as s:
            s.add(ev)
            s.commit()
            s.refresh(ev)
            data = serialize(ev)
        self.broadcast({"channel": "event", "data": data})
        return data

    def broadcast(self, msg: dict[str, Any]) -> None:
        """Push a raw message (event, stats tick, live sightings) to every socket."""
        if self._loop is None:
            return
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            self._loop.call_soon_threadsafe(self._offer, q, msg)

    @staticmethod
    def _offer(q: asyncio.Queue, msg: dict[str, Any]) -> None:
        if q.full():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
        q.put_nowait(msg)


bus = EventBus()
