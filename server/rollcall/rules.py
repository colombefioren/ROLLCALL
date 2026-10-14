"""Suspicious-activity rules evaluated on every processed frame.

Each rule keeps its own timer and a cooldown so one condition raises one alert, not one per frame.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import cv2
import numpy as np

from .config import settings
from .events import bus
from .faces import Face
from .gallery import Roster
from .models import Session
from .snapshots import save_snapshot


class Sighting:
    __slots__ = ("face", "student_id", "score")

    def __init__(self, face: Face, student_id: int | None, score: float) -> None:
        self.face = face
        self.student_id = student_id
        self.score = score


class RuleEngine:
    def __init__(self, roster: Roster) -> None:
        self.roster = roster
        self._unknown_since: datetime | None = None
        self._unknown_fired = False
        self._unknown_clear_since: datetime | None = None
        self._dark_since: datetime | None = None
        self.camera_blocked = False
        self._last_fired: dict[str, datetime] = {}
        self.brightness = 0.0

    def _cooled(self, key: str, now: datetime, seconds: int | None = None) -> bool:
        last = self._last_fired.get(key)
        window = timedelta(seconds=seconds or settings.alert_cooldown_s)
        if last is not None and now - last < window:
            return False
        self._last_fired[key] = now
        return True

    def evaluate(self, frame: np.ndarray, sightings: list[Sighting], session: Session | None, now: datetime) -> None:
        self._check_brightness(frame, now, session)
        if self.camera_blocked:
            return
        self._check_unknown(frame, sightings, now, session)
        self._check_crowding(frame, sightings, now, session)
        self._check_duplicates(frame, sightings, now, session)
        self._check_out_of_hours(frame, sightings, now, session)

    # -- rules ---------------------------------------------------------------

    def _check_brightness(self, frame: np.ndarray, now: datetime, session: Session | None) -> None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.brightness = float(gray.mean())
        dark = self.brightness < settings.dark_brightness
        if dark:
            self._dark_since = self._dark_since or now
            if not self.camera_blocked and (now - self._dark_since).total_seconds() >= settings.dark_frame_s:
                self.camera_blocked = True
                bus.publish(
                    kind="alert",
                    type="camera_blocked",
                    severity="critical",
                    message="Camera feed went dark. Lens covered or lights off.",
                    session_id=session.id if session else None,
                    snapshot=save_snapshot(frame, "camera_blocked"),
                    payload={"brightness": round(self.brightness, 1)},
                )
        else:
            self._dark_since = None
            if self.camera_blocked:
                self.camera_blocked = False
                bus.publish(
                    kind="system",
                    type="camera_restored",
                    message="Camera feed restored",
                    session_id=session.id if session else None,
                )

    def _check_unknown(self, frame: np.ndarray, sightings: list[Sighting], now: datetime, session: Session | None) -> None:
        unknown = [s for s in sightings if s.student_id is None]
        if not unknown:
            # One alert per episode: re-arm only after the room has been clear for a while.
            self._unknown_since = None
            self._unknown_clear_since = self._unknown_clear_since or now
            if self._unknown_fired and (now - self._unknown_clear_since).total_seconds() >= settings.unknown_rearm_s:
                self._unknown_fired = False
            return
        self._unknown_clear_since = None
        self._unknown_since = self._unknown_since or now
        if self._unknown_fired or (now - self._unknown_since).total_seconds() < settings.unknown_alert_s:
            return
        if not self._cooled("unknown_person", now):
            return
        self._unknown_fired = True
        biggest = max(unknown, key=lambda s: s.face.box[2] * s.face.box[3])
        bus.publish(
            kind="alert",
            type="unknown_person",
            severity="warning",
            message="Unrecognised person in the room" + (" during session" if session else ""),
            session_id=session.id if session else None,
            snapshot=save_snapshot(frame, "unknown", biggest.face.box),
            payload={"faces": len(sightings), "unknown": len(unknown), "best_score": round(biggest.score, 3)},
        )

    def _check_crowding(self, frame: np.ndarray, sightings: list[Sighting], now: datetime, session: Session | None) -> None:
        if len(sightings) <= settings.room_capacity:
            return
        if not self._cooled("crowding", now):
            return
        bus.publish(
            kind="alert",
            type="crowding",
            severity="warning",
            message=f"{len(sightings)} people in frame, room capacity is {settings.room_capacity}",
            session_id=session.id if session else None,
            snapshot=save_snapshot(frame, "crowding"),
            payload={"faces": len(sightings), "capacity": settings.room_capacity},
        )

    def _check_duplicates(self, frame: np.ndarray, sightings: list[Sighting], now: datetime, session: Session | None) -> None:
        seen: dict[int, int] = {}
        for s in sightings:
            if s.student_id is not None:
                seen[s.student_id] = seen.get(s.student_id, 0) + 1
        for sid, n in seen.items():
            if n < 2:
                continue
            if not self._cooled(f"duplicate_{sid}", now):
                continue
            name = self.roster.name(sid)
            bus.publish(
                kind="alert",
                type="duplicate_identity",
                severity="warning",
                message=f"{name} matched on {n} faces at once. Possible photo spoof.",
                session_id=session.id if session else None,
                student_id=sid,
                snapshot=save_snapshot(frame, "duplicate"),
                payload={"count": n},
            )

    def _check_out_of_hours(self, frame: np.ndarray, sightings: list[Sighting], now: datetime, session: Session | None) -> None:
        if session is not None or not sightings:
            return
        if not self._cooled("out_of_hours", now, settings.alert_cooldown_s * 3):
            return
        names = sorted({self.roster.name(s.student_id) for s in sightings})
        bus.publish(
            kind="alert",
            type="out_of_hours",
            severity="info",
            message=f"Activity with no session running: {', '.join(names)}",
            snapshot=save_snapshot(frame, "out_of_hours"),
            payload={"faces": len(sightings), "names": names},
        )

    def camera_lost(self, now: datetime) -> None:
        if self._cooled("camera_lost", now, settings.alert_cooldown_s * 5):
            bus.publish(
                kind="alert",
                type="camera_lost",
                severity="critical",
                message=f"Camera source {settings.camera_source!r} is not delivering frames",
            )
