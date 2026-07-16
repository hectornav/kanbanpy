"""
ws.py - WebSocket connection manager for live board sync.

Clients connect with ?token=<jwt>. When any client mutates the board, the API
broadcasts a lightweight {"type": "board:changed", "by": <user_id>} event and
every connected client reloads. Simple and correct for a small family instance.
"""
import asyncio

from fastapi import WebSocket

from .security import decode_access_token


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, token: str) -> bool:
        user_id = decode_access_token(token)
        if user_id is None:
            await websocket.close(code=4401)
            return False
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        return True

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        async with self._lock:
            targets = list(self._connections)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)


manager = ConnectionManager()
