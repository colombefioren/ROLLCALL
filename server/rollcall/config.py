"""Runtime settings, all overridable through environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    camera_source: str = field(default_factory=lambda: _env("ROLLCALL_CAMERA", "0"))
    db_path: Path = field(default_factory=lambda: Path(_env("ROLLCALL_DB", str(ROOT / "data" / "rollcall.db"))))
    snapshot_dir: Path = field(default_factory=lambda: Path(_env("ROLLCALL_SNAPSHOTS", str(ROOT / "data" / "snapshots"))))
    models_dir: Path = field(default_factory=lambda: Path(_env("ROLLCALL_MODELS", str(ROOT / "models"))))

    # Recognition
    match_threshold: float = field(default_factory=lambda: float(_env("ROLLCALL_MATCH_THRESHOLD", "0.40")))
    detect_score: float = field(default_factory=lambda: float(_env("ROLLCALL_DETECT_SCORE", "0.80")))
    process_fps: float = field(default_factory=lambda: float(_env("ROLLCALL_PROCESS_FPS", "6")))
    frame_width: int = field(default_factory=lambda: int(_env("ROLLCALL_FRAME_WIDTH", "960")))

    # Attendance rules
    leave_timeout_s: int = field(default_factory=lambda: int(_env("ROLLCALL_LEAVE_TIMEOUT", "45")))
    default_grace_min: int = field(default_factory=lambda: int(_env("ROLLCALL_GRACE_MIN", "10")))
    early_leave_margin_min: int = field(default_factory=lambda: int(_env("ROLLCALL_EARLY_LEAVE_MIN", "10")))
    confirm_sightings: int = field(default_factory=lambda: int(_env("ROLLCALL_CONFIRM_SIGHTINGS", "3")))

    # Suspicious-activity rules
    unknown_alert_s: int = field(default_factory=lambda: int(_env("ROLLCALL_UNKNOWN_ALERT", "6")))
    unknown_rearm_s: int = field(default_factory=lambda: int(_env("ROLLCALL_UNKNOWN_REARM", "30")))
    dark_frame_s: int = field(default_factory=lambda: int(_env("ROLLCALL_DARK_FRAME", "4")))
    dark_brightness: int = field(default_factory=lambda: int(_env("ROLLCALL_DARK_LEVEL", "28")))
    room_capacity: int = field(default_factory=lambda: int(_env("ROLLCALL_CAPACITY", "30")))
    alert_cooldown_s: int = field(default_factory=lambda: int(_env("ROLLCALL_ALERT_COOLDOWN", "60")))

    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(_env("ROLLCALL_CORS", "http://localhost:3000,http://127.0.0.1:3000").split(","))
    )

    @property
    def yunet_path(self) -> Path:
        return self.models_dir / "face_detection_yunet_2023mar.onnx"

    @property
    def sface_path(self) -> Path:
        return self.models_dir / "face_recognition_sface_2021dec.onnx"


settings = Settings()
