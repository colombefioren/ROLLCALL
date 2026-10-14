# Rollcall architecture

## Shape

Two runtimes, one repository.

```
camera ──► server/ (FastAPI + OpenCV worker thread) ──► SQLite
                │  REST · MJPEG · WebSocket
                ▼
            web/ (Next.js dashboard, browser only)
```

The vision worker and the API share a process on purpose. The worker needs the recognizer, the roster and the attendance tracker; the API needs the same objects for enrollment and session control. Splitting them would add a message bus and a second deploy for no gain at this scale (one camera, one room).

## Decisions

### Modular monolith over services
A single FastAPI process hosts the camera loop (thread), the rules, the attendance state machine and the HTTP surface. Modules are separated by concern (`faces`, `pipeline`, `attendance`, `rules`, `events`, `routers/*`) so a later split (for example one vision worker per camera) is a move, not a rewrite. The only shared mutable state crossing the thread boundary is the event bus, the latest frame, and the tracker, each behind a lock.

**Rejected:** a separate Python vision worker publishing over Redis or MQTT to a Node API. More moving parts, two languages for one feature, and the demo would depend on a broker.

### OpenCV YuNet + SFace instead of dlib or InsightFace
Both models ship as small ONNX files and run through `opencv-python-headless` with no compiler, no CUDA and no extra runtime. YuNet detects at 320x320 in a few milliseconds on CPU; SFace gives a 128-d embedding with a documented cosine threshold. Accuracy is below ArcFace-class models, but installation is one `pip install`, which matters for a hackathon and for running on whatever laptop sits in the classroom.

**Rejected:** `face_recognition` (dlib compile, slow on CPU), InsightFace (build issues on recent Python, larger models), a browser-side recognizer (ties the camera to a browser tab and leaks the logic into the client).

### SQLite with WAL
One file, no service, survives restarts. Writes are low (a few rows per event). WAL mode lets the API read while the worker thread writes. Embeddings are stored as raw float32 bytes and loaded into a NumPy matrix at startup and after every enrollment, so matching is one matrix-vector product.

### Presence as a state machine, not raw sightings
Frames are noisy. The tracker requires `confirm_sightings` consecutive matched frames before a check-in, and `leave_timeout_s` of absence before a check-out. Returning after a check-out is a distinct `returned` event rather than a second check-in, so the sheet keeps one row per student with an exit counter. Session end is the only place absentees are written, because until then "not seen yet" is the honest status.

### Rules with cooldowns and re-arming
Every suspicious condition is a small class-level timer: condition must persist for N seconds, fires once, then waits for a cooldown and, for the unknown-person rule, for the room to clear before it can fire again. This keeps one real event from turning into a page of identical alerts.

### Push over polling
The WebSocket carries two channels: `event` (anything persisted) and `live` (camera status and who is in frame, once per second). The dashboard uses SWR for data and revalidates the affected keys when an event arrives, so the UI is consistent with the database rather than with an in-memory copy of it.

## What is deliberately not built

- Authentication. The dashboard is meant for one teacher's laptop on a LAN. Put it behind a reverse proxy with auth before exposing it.
- Liveness or anti-spoofing beyond the duplicate-face rule.
- Multi-camera. The pipeline is written for one source; a second camera would be a second process with its own `ROLLCALL_CAMERA` and a shared database.
- Migrations. Tables are created on boot; delete `server/data/rollcall.db` to reset.

## Failure modes

| Failure | Behaviour |
|---------|-----------|
| Camera disconnects | `camera_lost` critical alert after 3 s, capture reopened every 3 s, dashboard shows "No camera" |
| Lens covered | `camera_blocked` critical alert after 4 s dark, `camera_restored` when light returns, rules paused meanwhile |
| Server down | Dashboard header shows "Server offline", socket reconnects every 2 s, MJPEG resumes on reconnect |
| Face matches two students | Highest cosine wins; enrollment of a face already matching someone else is refused with the score |

## Operability

- Logs: uvicorn stdout. Events: `/events`. Health: `/health` (includes camera status).
- Reset: stop the server, delete `server/data/`.
- Tuning: all thresholds are environment variables (see README).
