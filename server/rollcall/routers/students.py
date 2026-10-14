"""Student roster and face enrollment."""

from __future__ import annotations

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session as DbSession, func, select

from ..db import get_db
from ..events import bus
from ..faces import largest_face
from ..models import Attendance, FaceTemplate, Student
from ..snapshots import save_photo
from ..state import state

router = APIRouter(prefix="/students", tags=["students"])


class StudentIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=80)
    group: str = Field(default="", max_length=40)


def _out(st: Student, templates: int, sessions_present: int = 0) -> dict:
    return {
        "id": st.id,
        "code": st.code,
        "name": st.name,
        "group": st.group,
        "photo": f"/photos/{st.photo}" if st.photo else None,
        "templates": templates,
        "created_at": st.created_at.isoformat(),
    }


@router.get("")
def list_students(s: DbSession = Depends(get_db)) -> list[dict]:
    counts = dict(
        s.exec(select(FaceTemplate.student_id, func.count(FaceTemplate.id)).group_by(FaceTemplate.student_id)).all()
    )
    return [_out(st, counts.get(st.id, 0)) for st in s.exec(select(Student).order_by(Student.name)).all()]


@router.post("", status_code=201)
def create_student(body: StudentIn, s: DbSession = Depends(get_db)) -> dict:
    if s.exec(select(Student).where(Student.code == body.code)).first():
        raise HTTPException(409, f"Student code {body.code!r} already exists")
    st = Student(code=body.code.strip(), name=body.name.strip(), group=body.group.strip())
    s.add(st)
    s.commit()
    s.refresh(st)
    state().roster.reload()
    return _out(st, 0)


@router.get("/{student_id}")
def get_student(student_id: int, s: DbSession = Depends(get_db)) -> dict:
    st = s.get(Student, student_id)
    if st is None:
        raise HTTPException(404, "Student not found")
    templates = len(s.exec(select(FaceTemplate).where(FaceTemplate.student_id == student_id)).all())
    history = s.exec(
        select(Attendance).where(Attendance.student_id == student_id).order_by(Attendance.id.desc()).limit(30)  # type: ignore[union-attr]
    ).all()
    return {**_out(st, templates), "history": [a.model_dump(mode="json") for a in history]}


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, s: DbSession = Depends(get_db)) -> None:
    st = s.get(Student, student_id)
    if st is None:
        raise HTTPException(404, "Student not found")
    for t in s.exec(select(FaceTemplate).where(FaceTemplate.student_id == student_id)).all():
        s.delete(t)
    s.delete(st)
    s.commit()
    state().roster.reload()


def _enroll_frame(student_id: int, frame: np.ndarray, source: str, s: DbSession) -> dict:
    st = s.get(Student, student_id)
    if st is None:
        raise HTTPException(404, "Student not found")
    app = state()
    faces = app.engine.detect(frame)
    face = largest_face(faces)
    if face is None:
        raise HTTPException(422, "No face found in the image. Use a well-lit, front-facing photo.")
    emb = app.engine.embed(frame, face)
    existing = app.engine.match(emb)
    if existing.student_id is not None and existing.student_id != student_id:
        other = app.roster.name(existing.student_id)
        raise HTTPException(409, f"This face already matches {other} (score {existing.score:.2f})")
    s.add(FaceTemplate(student_id=student_id, embedding=emb.astype(np.float32).tobytes()))
    if not st.photo:
        st.photo = save_photo(frame, student_id, face.box)
        s.add(st)
    s.commit()
    app.roster.reload()
    count = len(s.exec(select(FaceTemplate).where(FaceTemplate.student_id == student_id)).all())
    bus.publish(
        kind="system",
        type="enrolled",
        message=f"{st.name} enrolled ({count} face template{'s' if count != 1 else ''})",
        student_id=student_id,
        payload={"source": source, "faces_in_image": len(faces), "templates": count},
    )
    return {"student_id": student_id, "templates": count, "photo": f"/photos/{st.photo}", "faces_in_image": len(faces)}


@router.post("/{student_id}/enroll")
async def enroll_upload(student_id: int, image: UploadFile = File(...), s: DbSession = Depends(get_db)) -> dict:
    data = await image.read()
    arr = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise HTTPException(422, "Could not decode image")
    h, w = arr.shape[:2]
    if w > 1280:
        arr = cv2.resize(arr, (1280, int(h * 1280 / w)), interpolation=cv2.INTER_AREA)
    return _enroll_frame(student_id, arr, "upload", s)


@router.post("/{student_id}/enroll/capture")
def enroll_capture(student_id: int, s: DbSession = Depends(get_db)) -> dict:
    frame = state().pipeline.latest_frame()
    if frame is None:
        raise HTTPException(503, "Camera has not delivered a frame yet")
    return _enroll_frame(student_id, frame, "camera", s)
