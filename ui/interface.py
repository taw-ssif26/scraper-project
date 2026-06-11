import asyncio
import threading
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import Orchestrator, State

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Background event loop for Playwright ─────────────────────────────────────
_loop: asyncio.AbstractEventLoop = None
_orchestrator: Orchestrator = None
_log_lines: list[str] = []


def _start_background_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


threading.Thread(target=_start_background_loop, daemon=True).start()


def _run_async(coro):
    asyncio.run_coroutine_threadsafe(coro, _loop)


# ── API Routes ────────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str
    task: str


@app.post("/api/start")
def start(req: ScrapeRequest):
    global _orchestrator, _log_lines

    if not req.url.strip():
        return JSONResponse({"ok": False, "error": "URL is required"})
    if not req.task.strip():
        return JSONResponse({"ok": False, "error": "Task is required"})

    _log_lines = []

    def log(msg):
        _log_lines.append(msg)

    _orchestrator = Orchestrator(log_callback=log)
    _run_async(_orchestrator.run(req.url.strip(), req.task.strip()))
    return JSONResponse({"ok": True})


@app.post("/api/stop")
def stop():
    if _orchestrator:
        _orchestrator.stop()
    return JSONResponse({"ok": True})


@app.post("/api/resume")
def resume():
    if _orchestrator:
        _orchestrator.resolve_captcha()
    return JSONResponse({"ok": True})


@app.get("/api/status")
def status():
    if not _orchestrator:
        return JSONResponse({
            "state": "idle",
            "logs": [],
            "records": 0,
            "output": None,
            "captcha": False,
        })
    return JSONResponse({
        "state": _orchestrator.state.value,
        "logs": _log_lines[-100:],
        "records": len(_orchestrator.records),
        "output": _orchestrator.output_paths.get("csv") if _orchestrator.output_paths else None,
        "captcha": _orchestrator.state == State.PAUSED,
    })


@app.get("/api/download")
def download():
    if not _orchestrator or not _orchestrator.output_paths:
        return JSONResponse({"error": "No file available"}, status_code=404)
    csv_path = _orchestrator.output_paths.get("csv")
    if not csv_path or not os.path.exists(csv_path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=os.path.basename(csv_path)
    )



