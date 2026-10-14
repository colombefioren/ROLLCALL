"""JPEG evidence files attached to alerts and enrollments."""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from .config import settings

settings.snapshot_dir.mkdir(parents=True, exist_ok=True)
PHOTO_DIR = settings.snapshot_dir.parent / "photos"
PHOTO_DIR.mkdir(parents=True, exist_ok=True)


def crop(frame: np.ndarray, box: tuple[int, int, int, int], margin: float = 0.4) -> np.ndarray:
    x, y, w, h = box
    mx, my = int(w * margin), int(h * margin)
    fh, fw = frame.shape[:2]
    x0, y0 = max(0, x - mx), max(0, y - my)
    x1, y1 = min(fw, x + w + mx), min(fh, y + h + my)
    return frame[y0:y1, x0:x1]


def save_snapshot(frame: np.ndarray, label: str, box: tuple[int, int, int, int] | None = None) -> str:
    img = crop(frame, box) if box else frame
    name = f"{label}_{int(time.time() * 1000)}.jpg"
    cv2.imwrite(str(settings.snapshot_dir / name), img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return name


def save_photo(frame: np.ndarray, student_id: int, box: tuple[int, int, int, int]) -> str:
    img = crop(frame, box, margin=0.5)
    side = max(img.shape[:2])
    img = cv2.resize(img, (256, int(256 * img.shape[0] / side)) if side == img.shape[1] else (int(256 * img.shape[1] / side), 256))
    name = f"{student_id}.jpg"
    cv2.imwrite(str(PHOTO_DIR / name), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return name
