"""FastAPI entrypoint. Run with: uvicorn rollcall.main:app --reload"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import state as app_state
from .config import settings
from .db import init_db
from .events import bus
from .routers import events, live, sessions, students
from .snapshots import PHOTO_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    bus.bind(asyncio.get_running_loop())
    st = app_state.boot()
    st.pipeline.start()
    try:
        yield
    finally:
        st.pipeline.stop()
        st.pipeline.join(timeout=3)


app = FastAPI(title="Rollcall", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(students.router)
app.include_router(sessions.router)
app.include_router(events.router)
app.include_router(live.router)
app.mount("/snapshots", StaticFiles(directory=str(settings.snapshot_dir)), name="snapshots")
app.mount("/photos", StaticFiles(directory=str(PHOTO_DIR)), name="photos")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "camera": app_state.state().pipeline.status()}
