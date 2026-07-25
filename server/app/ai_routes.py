"""
ai_routes.py - AI planner endpoint: turn a project idea into board tasks.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from . import ai, db
from .deps import get_current_user
from .schemas import AiConfigIn, AiPlanRequest
from .ws import manager

router = APIRouter(prefix="/api", tags=["ai"])


@router.get("/ai/status")
def ai_status(current=Depends(get_current_user)):
    """Lets the UI show/hide the planner button without exposing the key."""
    return {"enabled": ai.configured(current["org_id"])}


@router.get("/ai/config")
def get_ai_config(current=Depends(get_current_user)):
    """Non-secret AI config for the settings form. Never returns the API key."""
    org_id = current["org_id"]
    c = ai.config(org_id)
    return {
        "provider": c["provider"],
        "anthropic_key_set": ai.anthropic_key_set(org_id),
        "anthropic_model": c["anthropic_model"],
        "openai_base_url": c["openai_base_url"],
        "openai_key_set": ai.openai_key_set(org_id),
        "openai_model": c["openai_model"],
        "ollama_url": c["ollama_url"],
        "ollama_model": c["ollama_model"],
        "enabled": ai.configured(org_id),
        "can_edit": current["is_org_admin"],
    }


@router.put("/ai/config")
def set_ai_config(req: AiConfigIn, current=Depends(get_current_user)):
    if not current["is_org_admin"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Solo el administrador de la organización puede cambiar la IA.")
    org_id = current["org_id"]
    db.set_setting(org_id, "ai_provider", req.provider)
    # API key is write-only: only overwrite when a new value is provided.
    if req.anthropic_api_key:
        db.set_setting(org_id, "anthropic_api_key", req.anthropic_api_key.strip())
    if req.anthropic_model:
        db.set_setting(org_id, "anthropic_model", req.anthropic_model.strip())
    if req.openai_base_url:
        db.set_setting(org_id, "openai_base_url", req.openai_base_url.strip())
    if req.openai_api_key:
        db.set_setting(org_id, "openai_api_key", req.openai_api_key.strip())
    if req.openai_model:
        db.set_setting(org_id, "openai_model", req.openai_model.strip())
    if req.ollama_url:
        db.set_setting(org_id, "ollama_url", req.ollama_url.strip())
    if req.ollama_model:
        db.set_setting(org_id, "ollama_model", req.ollama_model.strip())
    return {"enabled": ai.configured(org_id)}


@router.post("/boards/{board_id}/ai-plan", status_code=status.HTTP_201_CREATED)
async def ai_plan(board_id: int, req: AiPlanRequest, current=Depends(get_current_user)):
    if not ai.configured(current["org_id"]):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "El planificador con IA no está configurado en el servidor.")
    if not db.can_access_board(current["id"], board_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this board.")

    try:
        tasks = await run_in_threadpool(ai.generate_plan, req.idea, current["org_id"])
    except Exception as exc:  # network / API / parse errors
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"La IA no pudo generar el plan: {exc}")

    created = 0
    for task in tasks:
        if task.get("text"):
            if db.create_task(current["id"], board_id, task) is not None:
                created += 1
    await manager.broadcast({"type": "board:changed", "by": current["id"]})
    return {"created": created}
