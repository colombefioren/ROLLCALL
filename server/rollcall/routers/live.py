"""Live camera view (MJPEG), WebSocket event stream, and dashboard stats."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlmodel import Session as DbSession, select

from ..db import get_db
from ..events import bus
from ..models import Attendance, Event, Student
from ..state import state

router = APIRouter(tags=["live"])
BOUNDARY = b"--rollcallframe"


async def _mjpeg():
    p = state().pipeline
    last: bytes | None = None
    while True:
        jpeg = p.latest_jpeg()
        if jpeg is not None and jpeg is not last:
            last = jpeg
            yield BOUNDARY + b"\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
        await asyncio.sleep(1.0 / 12)


@router.get("/stream.mjpg")
def stream() -> StreamingResponse:
    return StreamingResponse(
        _mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=rollcallframe",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/stats")
def stats(s: DbSession = Depends(get_db)) -> dict:
    app = state()
    sess = app.tracker.session
    counts = {"present": 0, "late": 0, "left": 0, "absent": 0, "pending": 0}
    enrolled = len(s.exec(select(Student.id)).all())
    if sess is not None:
        rows = s.exec(select(Attendance).where(Attendance.session_id == sess.id)).all()
        for r in rows:
            counts[r.status] = counts.get(r.status, 0) + 1
        counts["pending"] = max(0, enrolled - len(rows))
    unacked = len(s.exec(select(Event.id).where(Event.kind == "alert", Event.acknowledged == False)).all())  # noqa: E712
    return {
        "session": None if sess is None else {"id": sess.id, "name": sess.name, "started_at": sess.started_at.isoformat(),
                                             "planned_end_at": sess.planned_end_at.isoformat() if sess.planned_end_at else None,
                                             "grace_minutes": sess.grace_minutes},
        "counts": counts,
        "enrolled": enrolled,
        "unacknowledged_alerts": unacked,
        "camera": app.pipeline.status(),
    }


@router.websocket("/ws")
async def ws(socket: WebSocket) -> None:
    await socket.accept()
    q = bus.subscribe()
    try:
        await socket.send_text(json.dumps({"channel": "live", "data": state().pipeline.status()}))
        while True:
            msg = await q.get()
            await socket.send_text(json.dumps(msg))
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(q)
