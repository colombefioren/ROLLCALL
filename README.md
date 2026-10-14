<div align="center">
  <h1>Rollcall</h1>
  <p><b>Camera attendance for classrooms.</b> One camera at the door or the front of the room checks students in, notices when they leave, raises alerts when something looks off, and keeps the full log.</p>
  <p>
    <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" />
    <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" />
    <img alt="OpenCV" src="https://img.shields.io/badge/OpenCV-YuNet%20%2B%20SFace-5C3EE8?style=flat-square&logo=opencv&logoColor=white" />
    <img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=nextdotjs&logoColor=white" />
    <img alt="SQLite" src="https://img.shields.io/badge/SQLite-WAL-003B57?style=flat-square&logo=sqlite&logoColor=white" />
  </p>
</div>

---

## What it does

| Area | Behaviour |
|------|-----------|
| **Check-in** | A student is checked in after three consecutive matched frames. Arrivals after the grace period are marked **late**. |
| **Check-out** | Out of view for 45 s means **left**, with the exit time and minutes in the room. Coming back flips them to present again and is logged as a return. |
| **Session close** | Ending a session fills in absentees, closes open check-outs and emits a summary. Sheets export to CSV. |
| **Alerts** | Unknown person in the room, camera covered or lights off, camera feed lost, more faces than room capacity, the same face matched twice at once (photo held to the lens), people in the room with no session running, and students leaving early. Alerts carry a JPEG snapshot and can be acknowledged. |
| **Logs** | Every check-in, exit, return, alert and system event is persisted and searchable by kind, severity, session and text. |
| **Enrollment** | Add a student, then enroll a face from an uploaded photo or straight from the live camera. Several templates per student are allowed. Faces that already match another student are rejected. |

## Stack

- **server/** FastAPI + OpenCV. YuNet detects faces, SFace embeds them (128-d), cosine similarity matches against the enrolled gallery. SQLite stores everything. A worker thread runs the camera loop; the API exposes REST, an MJPEG stream and a WebSocket that pushes events and a once-per-second live status.
- **web/** Next.js 16, Tailwind v4, SWR, Motion, Phosphor icons. Five screens: Live, Attendance, Alerts, Logs, Students. Light and dark themes.

Architecture notes and decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it

Requirements: Python 3.12 (through [uv](https://docs.astral.sh/uv/)), Node 20+, a webcam, an RTSP camera, or a video file.

```bash
# vision service
cd server
./scripts/download_models.sh          # two ONNX files from the OpenCV Zoo
uv sync                               # creates .venv from pyproject + uv.lock
.venv/bin/uvicorn rollcall.main:app --port 8000 --reload

# dashboard
cd web
npm install
npm run dev                            # http://localhost:3000
```

`./dev.sh` at the repo root does both.

### Configuration

Environment variables on the server (see `server/.env.example`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `ROLLCALL_CAMERA` | `0` | Device index, `rtsp://` URL, or a video file (files loop, handy for demos) |
| `ROLLCALL_MATCH_THRESHOLD` | `0.40` | Cosine similarity needed to accept a match |
| `ROLLCALL_PROCESS_FPS` | `6` | Frames analysed per second |
| `ROLLCALL_LEAVE_TIMEOUT` | `45` | Seconds unseen before a student is marked as left |
| `ROLLCALL_GRACE_MIN` | `10` | Default late threshold for new sessions |
| `ROLLCALL_CAPACITY` | `30` | Faces above this raise an overcrowding alert |
| `ROLLCALL_UNKNOWN_ALERT` | `6` | Seconds an unknown face must persist before alerting |
| `ROLLCALL_DARK_LEVEL` | `28` | Mean brightness below this counts as a covered camera |

The dashboard reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

### Bulk enrollment

Drop photos named `CODE__Full Name.jpg` (optionally `CODE__Full Name__Group.jpg`) in a folder and run:

```bash
cd server && .venv/bin/python scripts/enroll_folder.py path/to/photos
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/stats` | Session counts, open alerts, camera status |
| `GET` | `/stream.mjpg` | Annotated live video |
| `WS` | `/ws` | `{"channel":"event"}` and `{"channel":"live"}` messages |
| `GET/POST` | `/students`, `/students/{id}/enroll`, `/students/{id}/enroll/capture` | Roster and enrollment |
| `GET/POST` | `/sessions`, `/sessions/active`, `/sessions/end`, `/sessions/{id}/attendance.csv` | Sessions and sheets |
| `GET` | `/events`, `/alerts` | Log and alert queries with filters and cursor pagination |
| `POST` | `/alerts/{id}/ack`, `/alerts/ack-all` | Acknowledge |

Interactive docs at `http://localhost:8000/docs`.

## Limits worth knowing

- SFace on CPU handles a classroom-sized crowd at 6 fps on a laptop, but recognition quality drops for faces under about 60 px. Put the camera where people pass close to it.
- Nothing stops a printed photo from being recognised beyond the duplicate-face rule. Liveness detection is out of scope.
- Face data stays on the machine running the server: embeddings and snapshots live in `server/data/`, which is git-ignored.
