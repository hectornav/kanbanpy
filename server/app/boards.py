"""
boards.py - Board management: list/create/update/delete, members, activity.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from . import db
from .deps import get_current_user
from .schemas import BoardCreate, BoardUpdate
from .ws import manager

router = APIRouter(prefix="/api/boards", tags=["boards"])


async def _notify(user_id: int) -> None:
    await manager.broadcast({"type": "board:changed", "by": user_id})


@router.get("")
def list_boards(current=Depends(get_current_user)):
    boards = db.list_boards(current["id"])
    if not boards:
        db.ensure_default_board(current["id"], current["org_id"])
        boards = db.list_boards(current["id"])
    return boards


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_board(board: BoardCreate, current=Depends(get_current_user)):
    board_id = db.create_board(current["id"], current["org_id"], board.name, board.color)
    await _notify(current["id"])
    return {"id": board_id}


@router.put("/{board_id}")
async def update_board(board_id: int, board: BoardUpdate, current=Depends(get_current_user)):
    ok = db.update_board(board_id, current["id"], board.name, board.color,
                         board.is_shared, board.member_ids)
    if not ok:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the board owner can change it.")
    await _notify(current["id"])
    return {"detail": "updated"}


@router.delete("/{board_id}")
async def delete_board(board_id: int, current=Depends(get_current_user)):
    ok = db.delete_board(board_id, current["id"])
    if not ok:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the board owner can delete it.")
    await _notify(current["id"])
    return {"detail": "deleted"}


@router.get("/{board_id}/members")
def board_members(board_id: int, current=Depends(get_current_user)):
    return {"member_ids": db.get_board_members(board_id)}


@router.get("/{board_id}/activity")
def board_activity(board_id: int, limit: int = 50, current=Depends(get_current_user)):
    entries = db.get_activity(board_id, current["id"], limit)
    if entries is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this board.")
    return entries
