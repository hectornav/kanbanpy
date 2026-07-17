"""
tasks.py - Board contents and task routes.

Access is board-scoped: any member of a task's board can view, create, edit,
move, and archive tasks on it. Deletion is limited to the task owner or the
board owner.
"""
from fastapi import APIRouter, Depends, HTTPException, status

import asyncio

from . import db, push
from .deps import get_current_user
from .schemas import (CommentIn, MoveRequest, ReorderRequest, SubtaskIn,
                      SubtaskUpdate, TaskIn)
from .ws import manager

router = APIRouter(prefix="/api", tags=["tasks"])


async def _notify(user_id: int) -> None:
    await manager.broadcast({"type": "board:changed", "by": user_id})


async def _push_new_task(board_id: int, actor: dict, text: str) -> None:
    if not push.configured():
        return
    user_ids = db.board_notify_user_ids(board_id, exclude=actor["id"])
    if user_ids:
        payload = {"title": "Nueva tarea", "body": f"@{actor['username']}: {text}", "url": "/"}
        await asyncio.to_thread(push.notify_users, user_ids, payload)


@router.get("/boards/{board_id}/tasks")
def board_tasks(board_id: int, archived: bool = False, current=Depends(get_current_user)):
    tasks = db.get_board_tasks(current["id"], board_id, archived=archived)
    if tasks is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this board.")
    return tasks


@router.get("/users")
def users(current=Depends(get_current_user)):
    """User directory for the board-sharing picker (id + username only)."""
    return [u for u in db.list_users() if u["id"] != current["id"]]


@router.post("/boards/{board_id}/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(board_id: int, task: TaskIn, current=Depends(get_current_user)):
    task_id = db.create_task(current["id"], board_id, task.model_dump())
    if task_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this board.")
    await _notify(current["id"])
    await _push_new_task(board_id, current, task.text)
    return {"id": task_id}


@router.put("/tasks/{task_id}")
async def update_task(task_id: int, task: TaskIn, current=Depends(get_current_user)):
    if not db.update_task(task_id, current["id"], task.model_dump()):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit this task.")
    await _notify(current["id"])
    return {"detail": "updated"}


@router.post("/tasks/{task_id}/move")
async def move_task(task_id: int, req: MoveRequest, current=Depends(get_current_user)):
    if not db.move_task(task_id, current["id"], req.column_name, req.sort_order):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot move this task.")
    await _notify(current["id"])
    return {"detail": "moved"}


@router.post("/columns/reorder")
async def reorder(req: ReorderRequest, current=Depends(get_current_user)):
    if not db.reorder_column(current["id"], req.board_id, req.column_name, req.ordered_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid board or column.")
    await _notify(current["id"])
    return {"detail": "reordered"}


@router.post("/tasks/{task_id}/archive")
async def archive_task(task_id: int, current=Depends(get_current_user)):
    if not db.set_archived(task_id, current["id"], True):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot archive this task.")
    await _notify(current["id"])
    return {"detail": "archived"}


@router.post("/tasks/{task_id}/restore")
async def restore_task(task_id: int, current=Depends(get_current_user)):
    if not db.set_archived(task_id, current["id"], False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot restore this task.")
    await _notify(current["id"])
    return {"detail": "restored"}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, current=Depends(get_current_user)):
    if not db.delete_task(task_id, current["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only delete your own tasks.")
    await _notify(current["id"])
    return {"detail": "deleted"}


# ── Task detail: subtasks, comments, activity ──────────────────────────────────

@router.get("/tasks/{task_id}")
def task_detail(task_id: int, current=Depends(get_current_user)):
    detail = db.get_task_detail(task_id, current["id"])
    if detail is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this task.")
    return detail


@router.post("/tasks/{task_id}/subtasks", status_code=status.HTTP_201_CREATED)
async def add_subtask(task_id: int, req: SubtaskIn, current=Depends(get_current_user)):
    sid = db.add_subtask(task_id, current["id"], req.text)
    if sid is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this task.")
    await _notify(current["id"])
    return {"id": sid}


@router.put("/subtasks/{subtask_id}")
async def update_subtask(subtask_id: int, req: SubtaskUpdate, current=Depends(get_current_user)):
    if not db.update_subtask(subtask_id, current["id"], req.text, req.done):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this subtask.")
    await _notify(current["id"])
    return {"detail": "updated"}


@router.delete("/subtasks/{subtask_id}")
async def delete_subtask(subtask_id: int, current=Depends(get_current_user)):
    if not db.delete_subtask(subtask_id, current["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this subtask.")
    await _notify(current["id"])
    return {"detail": "deleted"}


@router.post("/tasks/{task_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(task_id: int, req: CommentIn, current=Depends(get_current_user)):
    cid = db.add_comment(task_id, current["id"], req.body)
    if cid is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this task.")
    await _notify(current["id"])
    return {"id": cid}


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: int, current=Depends(get_current_user)):
    if not db.delete_comment(comment_id, current["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot delete this comment.")
    await _notify(current["id"])
    return {"detail": "deleted"}
