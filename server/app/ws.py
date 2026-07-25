"""
ws.py - WebSocket connection manager for live board sync.

Clients connect with ?token=<jwt>. When any client mutates a board, the API
broadcasts a lightweight {"type": "board:changed", "by": <user_id>} event to
every connected client in the SAME organization, which then reloads. Simple
and correct for small teams sharing one instance.
"""
import asyncio

from fastapi import WebSocket

from . import db
from .security import decode_access_token


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, int] = {}  # websocket -> org_id
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, token: str) -> bool:
        user_id = decode_access_token(token)
        user = db.get_user_by_id(user_id) if user_id is not None else None
        if user is None:
            await websocket.close(code=4401)
            return False
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = user["org_id"]
        return True

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)

    async def broadcast(self, message: dict, org_id: int) -> None:
        async with self._lock:
            targets = [ws for ws, oid in self._connections.items() if oid == org_id]
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)


manager = ConnectionManager()
