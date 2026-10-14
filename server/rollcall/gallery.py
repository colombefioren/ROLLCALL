"""Loads enrolled face templates into the recognizer and keeps a name cache."""

from __future__ import annotations

import numpy as np
from sqlmodel import select

from .db import db
from .faces import FaceEngine
from .models import FaceTemplate, Student


class Roster:
    def __init__(self, engine: FaceEngine) -> None:
        self.engine = engine
        self.names: dict[int, str] = {}
        self.codes: dict[int, str] = {}
        self.reload()

    def reload(self) -> None:
        with db() as s:
            students = s.exec(select(Student)).all()
            templates = s.exec(select(FaceTemplate)).all()
        self.names = {st.id: st.name for st in students if st.id is not None}
        self.codes = {st.id: st.code for st in students if st.id is not None}
        rows = [
            (t.student_id, np.frombuffer(t.embedding, dtype=np.float32))
            for t in templates
            if t.student_id in self.names
        ]
        self.engine.set_gallery(rows)

    def name(self, student_id: int | None) -> str:
        if student_id is None:
            return "Unknown"
        return self.names.get(student_id, f"#{student_id}")
