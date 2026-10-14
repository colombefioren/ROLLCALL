"""Database tables. SQLite through SQLModel; one file, no migrations needed for a hackathon."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    group: str = ""
    photo: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class FaceTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    embedding: bytes
    created_at: datetime = Field(default_factory=utcnow)


class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    started_at: datetime = Field(default_factory=utcnow)
    planned_end_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    grace_minutes: int = 10


class Attendance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="session.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    status: str = "present"  # present | late | left | absent
    arrived_late: bool = False
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    sightings: int = 0
    leaves: int = 0


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=utcnow, index=True)
    kind: str = Field(index=True)  # attendance | alert | system
    type: str = Field(index=True)  # check_in, check_out, returned, unknown_person, ...
    severity: str = "info"  # info | warning | critical
    message: str
    session_id: Optional[int] = Field(default=None, foreign_key="session.id", index=True)
    student_id: Optional[int] = Field(default=None, foreign_key="student.id", index=True)
    snapshot: Optional[str] = None
    payload: str = "{}"
    acknowledged: bool = False
