"""
remote_db.py - Drop-in replacement for database.py that talks to the REST API.

Exposes the same function names the PyQt6 UI already calls, so switching the
desktop client from local SQLite to the shared NAS backend is a one-line import
change (see backend.py). A single module-level client holds the session token.
"""
from .api_client import ApiError, KanbanClient

_client = KanbanClient()


def client() -> KanbanClient:
    return _client


def init_db() -> None:
    # The server owns the schema; nothing to do on the client.
    return None


# ── Users / auth ───────────────────────────────────────────────────────────────

def authenticate_user(username: str, password: str):
    try:
        return _client.login(username, password)  # dict {id, username}
    except ApiError:
        return None


def register_user(username: str, password: str, security_q: str = "", security_a: str = ""):
    try:
        _client.register(username, password, security_q, security_a)
        return True, "Usuario registrado."
    except ApiError as e:
        return False, str(e)


def get_security_question(username: str):
    try:
        return _client.security_question(username)
    except ApiError:
        return None


def reset_password(username: str, answer: str, new_password: str):
    try:
        _client.reset_password(username, answer, new_password)
        return True, "Contraseña restablecida."
    except ApiError as e:
        return False, str(e)


def get_all_users():
    try:
        return _client.users()
    except ApiError:
        return []


# ── Tasks ────────────────────────────────────────────────────────────────────

def get_tasks_for_user(user_id: int) -> dict:
    # The server derives ownership from the token; user_id is ignored.
    return _client.board()


def add_task(owner_id: int, task_data: dict, shared_user_ids: list | None = None) -> int:
    payload = dict(task_data)
    payload["shared_user_ids"] = shared_user_ids or []
    return _client.create_task(payload)


def update_task(task_id: int, task_data: dict, shared_user_ids: list | None = None):
    payload = dict(task_data)
    if shared_user_ids is not None:
        payload["shared_user_ids"] = shared_user_ids
    _client.update_task(task_id, payload)


def move_task(task_id: int, new_column: str):
    _client.move_task(task_id, new_column)


def delete_task(task_id: int):
    _client.delete_task(task_id)


def get_shared_user_ids(task_id: int) -> list:
    try:
        return _client.task_shares(task_id)
    except ApiError:
        return []
