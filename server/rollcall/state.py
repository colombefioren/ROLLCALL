"""Process-wide singletons created at startup."""

from __future__ import annotations

from dataclasses import dataclass

from .attendance import AttendanceTracker
from .faces import FaceEngine
from .gallery import Roster
from .pipeline import Pipeline
from .rules import RuleEngine


@dataclass
class AppState:
    engine: FaceEngine
    roster: Roster
    tracker: AttendanceTracker
    rules: RuleEngine
    pipeline: Pipeline


_state: AppState | None = None


def boot() -> AppState:
    global _state
    engine = FaceEngine()
    roster = Roster(engine)
    tracker = AttendanceTracker(roster)
    rules = RuleEngine(roster)
    pipeline = Pipeline(engine, roster, tracker, rules)
    _state = AppState(engine, roster, tracker, rules, pipeline)
    return _state


def state() -> AppState:
    assert _state is not None, "app not booted"
    return _state
