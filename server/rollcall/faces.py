"""Face detection (YuNet) and recognition (SFace) on top of OpenCV's bundled DNN runtime."""

from __future__ import annotations

import threading
from dataclasses import dataclass

import cv2
import numpy as np

from .config import settings


@dataclass
class Face:
    box: tuple[int, int, int, int]  # x, y, w, h
    score: float
    raw: np.ndarray  # YuNet row: box + 5 landmarks + score, needed by alignCrop


@dataclass
class Match:
    student_id: int | None
    score: float


class FaceEngine:
    """Thread-safe wrapper. OpenCV models are not re-entrant, so every call takes the lock."""

    def __init__(self) -> None:
        if not settings.yunet_path.exists() or not settings.sface_path.exists():
            raise FileNotFoundError(
                f"ONNX models missing in {settings.models_dir}. Run scripts/download_models.sh."
            )
        self._lock = threading.Lock()
        self._detector = cv2.FaceDetectorYN.create(
            str(settings.yunet_path), "", (320, 320), settings.detect_score, 0.3, 5000
        )
        self._recognizer = cv2.FaceRecognizerSF.create(str(settings.sface_path), "")
        self._size = (0, 0)
        self._gallery_ids: list[int] = []
        self._gallery = np.zeros((0, 128), dtype=np.float32)

    # -- gallery -----------------------------------------------------------

    def set_gallery(self, rows: list[tuple[int, np.ndarray]]) -> None:
        with self._lock:
            if not rows:
                self._gallery_ids = []
                self._gallery = np.zeros((0, 128), dtype=np.float32)
                return
            self._gallery_ids = [sid for sid, _ in rows]
            mat = np.stack([self._normalize(e) for _, e in rows]).astype(np.float32)
            self._gallery = mat

    @property
    def gallery_size(self) -> int:
        return len(self._gallery_ids)

    # -- inference ---------------------------------------------------------

    def detect(self, frame: np.ndarray) -> list[Face]:
        h, w = frame.shape[:2]
        with self._lock:
            if (w, h) != self._size:
                self._detector.setInputSize((w, h))
                self._size = (w, h)
            _, rows = self._detector.detect(frame)
        if rows is None:
            return []
        faces: list[Face] = []
        for row in rows:
            x, y, bw, bh = (int(max(0, v)) for v in row[:4])
            faces.append(Face((x, y, bw, bh), float(row[-1]), row))
        return faces

    def embed(self, frame: np.ndarray, face: Face) -> np.ndarray:
        with self._lock:
            aligned = self._recognizer.alignCrop(frame, face.raw)
            feat = self._recognizer.feature(aligned)
        return self._normalize(feat.flatten())

    def match(self, embedding: np.ndarray) -> Match:
        with self._lock:
            if self._gallery.shape[0] == 0:
                return Match(None, 0.0)
            sims = self._gallery @ embedding.astype(np.float32)
            idx = int(np.argmax(sims))
            best = float(sims[idx])
            sid = self._gallery_ids[idx]
        if best < settings.match_threshold:
            return Match(None, best)
        return Match(sid, best)

    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        v = v.astype(np.float32).flatten()
        n = np.linalg.norm(v)
        return v / n if n > 0 else v


def largest_face(faces: list[Face]) -> Face | None:
    if not faces:
        return None
    return max(faces, key=lambda f: f.box[2] * f.box[3])
