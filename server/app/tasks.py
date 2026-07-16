"""
tasks.py - Board/task routes with per-user authorization.

Authorization model:
  * Anyone who can access a task (owner, globally shared, or explicitly shared)
    can view it, move it, and reorder columns.
  * Only the owner can edit a task's content, change its sharing, or delete it.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from . import db
from .deps import get_current_user
from .schemas import MoveRequest, ReorderRequest, TaskIn
from .ws import manager

router = APIRouter(prefix="/api", tags=["tasks"])


async def _notify(user_id: int) -> None:
    await manager.broadcast({"type": "board:changed", "by": user_id})


@router.get("/board")
def get_board(current=Depends(get_current_user)):
    return db.get_board(current["id"])


@router.get("/users")
def users(current=Depends(get_current_user)):
    """User directory for the 'share task with…' picker (id + username only)."""
    return [u for u in db.list_users() if u["id"] != current["id"]]


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskIn, current=Depends(get_current_user)):
    task_id = db.create_task(current["id"], task.model_dump(), task.shared_user_ids)
    await _notify(current["id"])
    return {"id": task_id}


@router.put("/tasks/{task_id}")
async def update_task(task_id: int, task: TaskIn, current=Depends(get_current_user)):
    ok = db.update_task(task_id, current["id"], task.model_dump(), task.shared_user_ids)
    if not ok:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only edit tasks you own.")
    await _notify(current["id"])
    return {"detail": "updated"}


@router.post("/tasks/{task_id}/move")
async def move_task(task_id: int, req: MoveRequest, current=Depends(get_current_user)):
    ok = db.move_task(task_id, current["id"], req.column_name, req.sort_order)
    if not ok:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot move this task.")
    await _notify(current["id"])
    return {"detail": "moved"}


@router.post("/columns/reorder")
async def reorder(req: ReorderRequest, current=Depends(get_current_user)):
    ok = db.reorder_column(current["id"], req.column_name, req.ordered_ids)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid column.")
    await _notify(current["id"])
    return {"detail": "reordered"}


@router.get("/tasks/{task_id}/shares")
def task_shares(task_id: int, current=Depends(get_current_user)):
    return {"shared_user_ids": db.get_shared_user_ids(task_id)}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, current=Depends(get_current_user)):
    ok = db.delete_task(task_id, current["id"])
    if not ok:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only delete tasks you own.")
    await _notify(current["id"])
    return {"detail": "deleted"}
