from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.collector import SnapshotCollector
from app.config import load_settings

settings = load_settings()
collector = SnapshotCollector(settings)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    collector.collect_once()
    collector.start_background_polling()
    yield


app = FastAPI(title="SLURM GPU Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")


def mb_to_gb(value: object) -> str:
    try:
        mb = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{mb / 1024:.1f}"


templates.env.filters["gb"] = mb_to_gb


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    snapshot = collector.get_snapshot()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "snapshot": snapshot,
            "refresh_seconds": settings.refresh_seconds,
            "data_source": settings.data_source,
        },
    )


@app.get("/api/status")
async def api_status() -> JSONResponse:
    return JSONResponse(collector.get_snapshot())


@app.get("/healthz")
async def healthz() -> JSONResponse:
    snapshot = collector.get_snapshot()
    return JSONResponse(
        {
            "status": snapshot.get("collection_status", "unknown"),
            "snapshot_time": snapshot.get("snapshot_time"),
            "errors": snapshot.get("errors", []),
        }
    )
