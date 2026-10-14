"""Camera worker: capture, detect, recognise, update attendance, evaluate rules, publish a live view."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import cv2
import numpy as np

from .attendance import AttendanceTracker
from .config import settings
from .events import bus
from .faces import FaceEngine
from .gallery import Roster
from .rules import RuleEngine, Sighting

GREEN = (96, 200, 120)
AMBER = (40, 170, 240)
RED = (70, 70, 235)
INK = (24, 24, 27)


class Pipeline(threading.Thread):
    def __init__(self, engine: FaceEngine, roster: Roster, tracker: AttendanceTracker, rules: RuleEngine) -> None:
        super().__init__(name="rollcall-vision", daemon=True)
        self.engine = engine
        self.roster = roster
        self.tracker = tracker
        self.rules = rules
        self._halt = threading.Event()
        self._frame_lock = threading.Lock()
        self._jpeg: bytes | None = None
        self._raw: np.ndarray | None = None
        self.camera_ok = False
        self.fps = 0.0
        self.last_sightings: list[dict] = []
        self._cap: cv2.VideoCapture | None = None
        src = settings.camera_source
        self._is_file = not src.isdigit() and "://" not in src

    # -- public --------------------------------------------------------------

    def stop(self) -> None:
        self._halt.set()

    def latest_jpeg(self) -> bytes | None:
        with self._frame_lock:
            return self._jpeg

    def latest_frame(self) -> np.ndarray | None:
        with self._frame_lock:
            return None if self._raw is None else self._raw.copy()

    def status(self) -> dict:
        return {
            "camera_ok": self.camera_ok,
            "camera_blocked": self.rules.camera_blocked,
            "brightness": round(self.rules.brightness, 1),
            "fps": round(self.fps, 1),
            "faces": len(self.last_sightings),
            "sightings": self.last_sightings,
            "gallery_size": self.engine.gallery_size,
            "source": settings.camera_source,
        }

    # -- capture -------------------------------------------------------------

    def _open(self) -> cv2.VideoCapture:
        src: int | str = int(settings.camera_source) if settings.camera_source.isdigit() else settings.camera_source
        cap = cv2.VideoCapture(src)
        if isinstance(src, int):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        return cap

    def run(self) -> None:
        self._cap = self._open()
        interval = 1.0 / settings.process_fps
        # Video files are read as fast as possible by OpenCV; pace them to their own frame rate.
        file_fps = self._cap.get(cv2.CAP_PROP_FPS) if self._is_file else 0.0
        file_interval = 1.0 / file_fps if file_fps and file_fps > 0 else 0.0
        next_frame_at = time.monotonic()
        last_tick = 0.0
        last_live = 0.0
        fail_streak = 0
        frames = 0
        fps_t0 = time.monotonic()
        while not self._halt.is_set():
            if file_interval:
                delay = next_frame_at - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                next_frame_at = max(next_frame_at + file_interval, time.monotonic() - file_interval)
            ok, frame = self._cap.read() if self._cap is not None else (False, None)
            if (not ok or frame is None) and self._is_file and self._cap is not None:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # demo videos loop forever
                ok, frame = self._cap.read()
            if not ok or frame is None:
                fail_streak += 1
                if fail_streak == 30:
                    self.camera_ok = False
                    self.rules.camera_lost(datetime.now(timezone.utc))
                if fail_streak % 30 == 0:
                    if self._cap is not None:
                        self._cap.release()
                    self._cap = self._open()
                time.sleep(0.1)
                continue
            if fail_streak:
                fail_streak = 0
            self.camera_ok = True
            frame = self._resize(frame)
            now_m = time.monotonic()
            if now_m - last_tick < interval:
                if not file_interval:
                    time.sleep(max(0.0, interval - (now_m - last_tick)) / 2)
                continue
            last_tick = now_m
            now = datetime.now(timezone.utc)
            sightings = self._process(frame, now)
            annotated = self._annotate(frame, sightings)
            ok_enc, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
            with self._frame_lock:
                self._raw = frame
                if ok_enc:
                    self._jpeg = buf.tobytes()
            frames += 1
            if now_m - fps_t0 >= 2:
                self.fps = frames / (now_m - fps_t0)
                frames, fps_t0 = 0, now_m
            if now_m - last_live >= 1:
                last_live = now_m
                bus.broadcast({"channel": "live", "data": self.status()})
        if self._cap is not None:
            self._cap.release()

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        if w <= settings.frame_width:
            return frame
        scale = settings.frame_width / w
        return cv2.resize(frame, (settings.frame_width, int(h * scale)), interpolation=cv2.INTER_AREA)

    # -- per frame -------------------------------------------------------------

    def _process(self, frame: np.ndarray, now: datetime) -> list[Sighting]:
        faces = self.engine.detect(frame)
        sightings: list[Sighting] = []
        for face in faces:
            emb = self.engine.embed(frame, face)
            m = self.engine.match(emb)
            sightings.append(Sighting(face, m.student_id, m.score))
        confirmed = {s.student_id for s in sightings if s.student_id is not None}
        self.tracker.observe(confirmed, now)
        self.rules.evaluate(frame, sightings, self.tracker.session, now)
        self.last_sightings = [
            {
                "student_id": s.student_id,
                "name": self.roster.name(s.student_id),
                "code": self.roster.codes.get(s.student_id) if s.student_id else None,
                "score": round(s.score, 3),
                "box": list(s.face.box),
            }
            for s in sightings
        ]
        return sightings

    def _annotate(self, frame: np.ndarray, sightings: list[Sighting]) -> np.ndarray:
        out = frame.copy()
        for s in sightings:
            x, y, w, h = s.face.box
            known = s.student_id is not None
            color = GREEN if known else AMBER
            label = f"{self.roster.name(s.student_id)}  {s.score:.2f}" if known else f"unknown  {s.score:.2f}"
            cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x, y - th - 10), (x + tw + 10, y), color, -1)
            cv2.putText(out, label, (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, INK, 1, cv2.LINE_AA)
        if self.rules.camera_blocked:
            cv2.putText(out, "CAMERA BLOCKED", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, RED, 2, cv2.LINE_AA)
        stamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(out, stamp, (out.shape[1] - 110, out.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (235, 235, 235), 1, cv2.LINE_AA)
        return out
