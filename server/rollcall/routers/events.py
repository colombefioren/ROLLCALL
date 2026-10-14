"""Event log, alerts, acknowledgement."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as DbSession, select

from ..db import get_db
from ..events import serialize
from ..models import Event, Student

router = APIRouter(tags=["events"])


def _with_names(events: list[Event], s: DbSession) -> list[dict]:
    ids = {e.student_id for e in events if e.student_id}
    names = {}
    if ids:
        names = {st.id: {"name": st.name, "code": st.code, "photo": f"/photos/{st.photo}" if st.photo else None}
                 for st in s.exec(select(Student).where(Student.id.in_(ids))).all()}  # type: ignore[union-attr]
    out = []
    for e in events:
        d = serialize(e)
        d["student"] = names.get(e.student_id)
        out.append(d)
    return out


@router.get("/events")
def list_events(
    kind: str | None = None,
    type: str | None = None,
    session_id: int | None = None,
    student_id: int | None = None,
    severity: str | None = None,
    q: str | None = None,
    before: int | None = Query(default=None, description="paginate: return events with id < before"),
    limit: int = Query(default=100, ge=1, le=500),
    s: DbSession = Depends(get_db),
) -> dict:
    stmt = select(Event)
    if kind:
        stmt = stmt.where(Event.kind == kind)
    if type:
        stmt = stmt.where(Event.type == type)
    if session_id is not None:
        stmt = stmt.where(Event.session_id == session_id)
    if student_id is not None:
        stmt = stmt.where(Event.student_id == student_id)
    if severity:
        stmt = stmt.where(Event.severity == severity)
    if q:
        stmt = stmt.where(Event.message.ilike(f"%{q}%"))  # type: ignore[union-attr]
    if before is not None:
        stmt = stmt.where(Event.id < before)  # type: ignore[operator]
    rows = s.exec(stmt.order_by(Event.id.desc()).limit(limit + 1)).all()  # type: ignore[union-attr]
    more = len(rows) > limit
    rows = rows[:limit]
    return {"items": _with_names(rows, s), "next_before": rows[-1].id if more and rows else None}


@router.get("/alerts")
def list_alerts(unacknowledged: bool = False, limit: int = Query(default=100, ge=1, le=500), s: DbSession = Depends(get_db)) -> dict:
    stmt = select(Event).where(Event.kind == "alert")
    if unacknowledged:
        stmt = stmt.where(Event.acknowledged == False)  # noqa: E712
    rows = s.exec(stmt.order_by(Event.id.desc()).limit(limit)).all()  # type: ignore[union-attr]
    unacked = len(s.exec(select(Event.id).where(Event.kind == "alert", Event.acknowledged == False)).all())  # noqa: E712
    return {"items": _with_names(rows, s), "unacknowledged": unacked}


@router.post("/alerts/{event_id}/ack")
def ack_alert(event_id: int, s: DbSession = Depends(get_db)) -> dict:
    ev = s.get(Event, event_id)
    if ev is None or ev.kind != "alert":
        raise HTTPException(404, "Alert not found")
    ev.acknowledged = True
    s.add(ev)
    s.commit()
    s.refresh(ev)
    return serialize(ev)


@router.post("/alerts/ack-all")
def ack_all(s: DbSession = Depends(get_db)) -> dict:
    rows = s.exec(select(Event).where(Event.kind == "alert", Event.acknowledged == False)).all()  # noqa: E712
    for ev in rows:
        ev.acknowledged = True
        s.add(ev)
    s.commit()
    return {"acknowledged": len(rows)}
