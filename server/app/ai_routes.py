"""
ai_routes.py - AI planner endpoint: turn a project idea into board tasks.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from . import ai, db
from .deps import get_current_user
from .schemas import AiPlanRequest
from .ws import manager

router = APIRouter(prefix="/api", tags=["ai"])


@router.get("/ai/status")
def ai_status():
    """Lets the UI show/hide the planner button without exposing the key."""
    return {"enabled": ai.configured()}


@router.post("/boards/{board_id}/ai-plan", status_code=status.HTTP_201_CREATED)
async def ai_plan(board_id: int, req: AiPlanRequest, current=Depends(get_current_user)):
    if not ai.configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "El planificador con IA no está configurado en el servidor.")
    if not db.can_access_board(current["id"], board_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this board.")

    try:
        tasks = await run_in_threadpool(ai.generate_plan, req.idea)
    except Exception as exc:  # network / API / parse errors
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"La IA no pudo generar el plan: {exc}")

    created = 0
    for task in tasks:
        if task.get("text"):
            if db.create_task(current["id"], board_id, task) is not None:
                created += 1
    await manager.broadcast({"type": "board:changed", "by": current["id"]})
    return {"created": created}
