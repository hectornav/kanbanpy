"""
main.py - FastAPI application entry point for Kanbanpy Pro.

Exposes the REST API, a WebSocket for live sync, and (optionally) serves the
built React PWA so a single container covers the whole hybrid stack.
"""
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import auth, boards, db, tasks
from .config import settings
from .ws import manager

app = FastAPI(title="Kanbanpy Pro API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(boards.router)
app.include_router(tasks.router)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    if not await manager.connect(websocket, token):
        return
    try:
        while True:
            # We don't process inbound messages; the socket is broadcast-only.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


# ── Serve the built PWA (single-container deployment) ───────────────────────────
_DIST = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
if settings.serve_static and _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        """Serve static files, falling back to index.html for client-side routes."""
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
