"""Sessions and their attendance sheets."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session as DbSession, select

from ..config import settings
from ..db import get_db
from ..models import Attendance, Session, Student
from ..state import state

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    grace_minutes: int = Field(default=settings.default_grace_min, ge=0, le=120)
    duration_minutes: int | None = Field(default=None, ge=5, le=600)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _session_out(sess: Session) -> dict:
    return {
        "id": sess.id,
        "name": sess.name,
        "started_at": _iso(sess.started_at),
        "planned_end_at": _iso(sess.planned_end_at),
        "ended_at": _iso(sess.ended_at),
        "grace_minutes": sess.grace_minutes,
        "active": sess.ended_at is None,
    }


def _sheet(sess: Session, s: DbSession) -> dict:
    students = {st.id: st for st in s.exec(select(Student)).all()}
    rows = s.exec(select(Attendance).where(Attendance.session_id == sess.id)).all()
    by_student = {r.student_id: r for r in rows}
    out = []
    for sid, st in students.items():
        r = by_student.get(sid)
        if r is None:
            status = "absent" if sess.ended_at else "pending"
            out.append({"student": _student_min(st), "status": status, "arrived_late": False,
                        "checked_in_at": None, "checked_out_at": None, "last_seen_at": None, "sightings": 0, "leaves": 0, "minutes_present": 0})
            continue
        end = r.checked_out_at or sess.ended_at or datetime.now(timezone.utc)
        if r.checked_in_at:
            start = r.checked_in_at.replace(tzinfo=timezone.utc) if r.checked_in_at.tzinfo is None else r.checked_in_at
            end = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
            minutes = max(0, int((end - start).total_seconds() // 60))
        else:
            minutes = 0
        out.append({
            "student": _student_min(st),
            "status": r.status,
            "arrived_late": r.arrived_late,
            "checked_in_at": _iso(r.checked_in_at),
            "checked_out_at": _iso(r.checked_out_at),
            "last_seen_at": _iso(r.last_seen_at),
            "sightings": r.sightings,
            "leaves": r.leaves,
            "minutes_present": minutes,
        })
    order = {"present": 0, "late": 1, "left": 2, "pending": 3, "absent": 4}
    out.sort(key=lambda r: (order.get(r["status"], 9), r["student"]["name"]))
    counts = {k: 0 for k in order}
    for r in out:
        counts[r["status"]] += 1
    return {"session": _session_out(sess), "rows": out, "counts": counts}


def _student_min(st: Student) -> dict:
    return {"id": st.id, "code": st.code, "name": st.name, "group": st.group, "photo": f"/photos/{st.photo}" if st.photo else None}


@router.get("")
def list_sessions(s: DbSession = Depends(get_db)) -> list[dict]:
    return [_session_out(x) for x in s.exec(select(Session).order_by(Session.started_at.desc())).all()]  # type: ignore[union-attr]


@router.get("/active")
def active_session(s: DbSession = Depends(get_db)) -> dict | None:
    sess = state().tracker.session
    if sess is None:
        return None
    fresh = s.get(Session, sess.id)
    return _sheet(fresh, s) if fresh else None


@router.post("", status_code=201)
def start_session(body: SessionIn) -> dict:
    sess = state().tracker.start_session(body.name.strip(), body.grace_minutes, body.duration_minutes)
    return _session_out(sess)


@router.post("/end")
def end_session() -> dict:
    sess = state().tracker.end_session()
    if sess is None:
        raise HTTPException(409, "No active session")
    return _session_out(sess)


@router.get("/{session_id}")
def get_session(session_id: int, s: DbSession = Depends(get_db)) -> dict:
    sess = s.get(Session, session_id)
    if sess is None:
        raise HTTPException(404, "Session not found")
    return _sheet(sess, s)


@router.get("/{session_id}/attendance.csv")
def export_csv(session_id: int, s: DbSession = Depends(get_db)) -> StreamingResponse:
    sess = s.get(Session, session_id)
    if sess is None:
        raise HTTPException(404, "Session not found")
    sheet = _sheet(sess, s)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["code", "name", "group", "status", "arrived_late", "checked_in_at", "checked_out_at", "minutes_present", "leaves"])
    for r in sheet["rows"]:
        st = r["student"]
        w.writerow([st["code"], st["name"], st["group"], r["status"], r["arrived_late"], r["checked_in_at"] or "",
                    r["checked_out_at"] or "", r["minutes_present"], r["leaves"]])
    buf.seek(0)
    fname = f"attendance_{sess.name.replace(' ', '_')}_{session_id}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={fname}"})
