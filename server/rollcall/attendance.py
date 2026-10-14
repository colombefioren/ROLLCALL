"""Presence state machine for the active session.

A student is checked in after `confirm_sightings` consecutive processed frames (filters one-frame
mismatches). They are marked as left once unseen for `leave_timeout_s`, and flip back to present
if they return. Ending a session fills in absentees and closes open check-outs.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from sqlmodel import select

from .config import settings
from .db import db
from .events import bus
from .gallery import Roster
from .models import Attendance, Session, Student


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class AttendanceTracker:
    def __init__(self, roster: Roster) -> None:
        self.roster = roster
        self._lock = threading.Lock()
        self.session: Session | None = None
        self._streak: dict[int, int] = {}
        self._last_seen: dict[int, datetime] = {}
        self._last_sweep = utcnow()
        self.reload_session()

    # -- session lifecycle ----------------------------------------------------

    def reload_session(self) -> None:
        with db() as s:
            active = s.exec(
                select(Session).where(Session.ended_at.is_(None)).order_by(Session.started_at.desc())  # type: ignore[union-attr]
            ).first()
        with self._lock:
            if active is None or self.session is None or active.id != self.session.id:
                self._streak.clear()
                self._last_seen.clear()
            self.session = active

    def start_session(self, name: str, grace_minutes: int, duration_minutes: int | None) -> Session:
        self.end_session()
        now = utcnow()
        sess = Session(
            name=name,
            started_at=now,
            grace_minutes=grace_minutes,
            planned_end_at=now + timedelta(minutes=duration_minutes) if duration_minutes else None,
        )
        with db() as s:
            s.add(sess)
            s.commit()
            s.refresh(sess)
        self.reload_session()
        bus.publish(
            kind="system",
            type="session_started",
            message=f"Session \"{name}\" started",
            session_id=sess.id,
            payload={"grace_minutes": grace_minutes, "duration_minutes": duration_minutes},
        )
        return sess

    def end_session(self) -> Session | None:
        with self._lock:
            sess = self.session
        if sess is None:
            return None
        now = utcnow()
        with db() as s:
            db_sess = s.get(Session, sess.id)
            if db_sess is None or db_sess.ended_at is not None:
                self.reload_session()
                return None
            db_sess.ended_at = now
            rows = s.exec(select(Attendance).where(Attendance.session_id == sess.id)).all()
            seen = {r.student_id for r in rows}
            present = left = 0
            for r in rows:
                if r.status in ("present", "late"):
                    r.checked_out_at = now
                    present += 1
                elif r.status == "left":
                    left += 1
                s.add(r)
            students = s.exec(select(Student)).all()
            absent = 0
            for st in students:
                if st.id not in seen:
                    s.add(Attendance(session_id=sess.id, student_id=st.id, status="absent"))
                    absent += 1
            s.commit()
            s.refresh(db_sess)
        self.reload_session()
        bus.publish(
            kind="system",
            type="session_ended",
            message=f"Session \"{db_sess.name}\" ended: {present} present at close, {left} left early, {absent} absent",
            session_id=db_sess.id,
            payload={"present": present, "left": left, "absent": absent},
        )
        return db_sess

    # -- per-frame update --------------------------------------------------------

    def observe(self, confirmed_ids: set[int], now: datetime) -> None:
        """Called once per processed frame with the student ids seen in that frame."""
        with self._lock:
            sess = self.session
            if sess is None:
                return
            for sid in list(self._streak):
                if sid not in confirmed_ids:
                    self._streak.pop(sid, None)
            newly_confirmed: list[int] = []
            for sid in confirmed_ids:
                n = self._streak.get(sid, 0) + 1
                self._streak[sid] = n
                if n >= settings.confirm_sightings:
                    self._last_seen[sid] = now
                    if n == settings.confirm_sightings:
                        newly_confirmed.append(sid)
        for sid in newly_confirmed:
            self._record_sighting(sess, sid, now)
        if (now - self._last_sweep).total_seconds() >= 2:
            self._last_sweep = now
            self._sweep(sess, now)

    def seen_recently(self) -> dict[int, datetime]:
        with self._lock:
            return dict(self._last_seen)

    def _record_sighting(self, sess: Session, sid: int, now: datetime) -> None:
        name = self.roster.name(sid)
        with db() as s:
            row = s.exec(
                select(Attendance).where(Attendance.session_id == sess.id, Attendance.student_id == sid)
            ).first()
            if row is None:
                late = now > _aware(sess.started_at) + timedelta(minutes=sess.grace_minutes)
                row = Attendance(
                    session_id=sess.id,
                    student_id=sid,
                    status="late" if late else "present",
                    arrived_late=late,
                    checked_in_at=now,
                    last_seen_at=now,
                    sightings=1,
                )
                s.add(row)
                s.commit()
                minutes_late = max(1, round((now - _aware(sess.started_at)).total_seconds() / 60))
                bus.publish(
                    kind="attendance",
                    type="check_in",
                    severity="warning" if late else "info",
                    message=f"{name} checked in" + (f" ({minutes_late} min late)" if late else ""),
                    session_id=sess.id,
                    student_id=sid,
                    payload={"late": late, "minutes_late": minutes_late if late else 0},
                )
                return
            row.sightings += 1
            row.last_seen_at = now
            if row.status == "left":
                row.status = "late" if row.arrived_late else "present"
                row.checked_out_at = None
                s.add(row)
                s.commit()
                bus.publish(
                    kind="attendance",
                    type="returned",
                    message=f"{name} is back in the room",
                    session_id=sess.id,
                    student_id=sid,
                )
                return
            s.add(row)
            s.commit()

    def _sweep(self, sess: Session, now: datetime) -> None:
        with self._lock:
            last_seen = dict(self._last_seen)
        timeout = timedelta(seconds=settings.leave_timeout_s)
        gone = [sid for sid, ts in last_seen.items() if now - ts > timeout]
        with self._lock:
            for sid in gone:
                self._last_seen.pop(sid, None)
                self._streak.pop(sid, None)
        planned_end = _aware(sess.planned_end_at)
        with db() as s:
            for sid, ts in last_seen.items():
                row = s.exec(
                    select(Attendance).where(Attendance.session_id == sess.id, Attendance.student_id == sid)
                ).first()
                if row is None or row.status not in ("present", "late"):
                    continue
                if sid not in gone:
                    row.last_seen_at = ts
                    s.add(row)
                    continue
                left_at = ts
                row.status = "left"
                row.checked_out_at = left_at
                row.leaves += 1
                s.add(row)
                s.commit()
                name = self.roster.name(sid)
                stayed = int((left_at - _aware(row.checked_in_at)).total_seconds() // 60) if row.checked_in_at else 0
                bus.publish(
                    kind="attendance",
                    type="check_out",
                    message=f"{name} left the room after {stayed} min",
                    session_id=sess.id,
                    student_id=sid,
                    ts=left_at,
                    payload={"minutes_present": stayed},
                )
                early_by = planned_end and (planned_end - left_at) > timedelta(minutes=settings.early_leave_margin_min)
                if early_by:
                    remaining = int((planned_end - left_at).total_seconds() // 60)
                    bus.publish(
                        kind="alert",
                        type="left_early",
                        severity="warning",
                        message=f"{name} left {remaining} min before the session ends",
                        session_id=sess.id,
                        student_id=sid,
                        payload={"minutes_remaining": remaining},
                    )
            s.commit()
