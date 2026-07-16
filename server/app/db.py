"""
db.py - SQLite persistence layer for the Kanbanpy Pro backend.

Runs in WAL mode so multiple readers (PWA + desktop client) don't block each
other. Security answers are stored hashed; the old plaintext scheme is gone.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import settings
from .security import hash_secret, verify_secret

COLUMNS = ("ToDo", "Doing", "Done")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_connection():
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username       TEXT    NOT NULL UNIQUE,
                password_hash  TEXT    NOT NULL,
                security_q     TEXT    DEFAULT '',
                security_a     TEXT    DEFAULT '',
                created_at     TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id     INTEGER NOT NULL,
                column_name  TEXT    NOT NULL DEFAULT 'ToDo',
                text         TEXT    NOT NULL,
                description  TEXT    DEFAULT '',
                priority     TEXT    DEFAULT 'Medium',
                tags         TEXT    DEFAULT '',
                due_date     TEXT    DEFAULT '',
                is_shared    INTEGER DEFAULT 0,
                sort_order   INTEGER DEFAULT 0,
                created_at   TEXT    DEFAULT '',
                updated_at   TEXT    DEFAULT '',
                FOREIGN KEY(owner_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS task_shares (
                task_id  INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                PRIMARY KEY (task_id, user_id),
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner_id);
            CREATE INDEX IF NOT EXISTS idx_shares_user ON task_shares(user_id);
            """
        )


# ── Row helpers ────────────────────────────────────────────────────────────────

def _task_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = [t for t in (d.get("tags") or "").split(",") if t]
    d["is_shared"] = bool(d.get("is_shared", 0))
    return d


# ── Users ────────────────────────────────────────────────────────────────────

def create_user(username: str, password: str, security_q: str = "", security_a: str = "") -> tuple[bool, str]:
    username = username.strip()
    if not username or not password:
        return False, "Username and password cannot be empty."
    answer_hash = hash_secret(security_a.strip().lower()) if security_a.strip() else ""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, security_q, security_a, created_at) "
                "VALUES (?,?,?,?,?)",
                (username, hash_secret(password), security_q.strip(), answer_hash, _now()),
            )
        return True, "User registered."
    except sqlite3.IntegrityError:
        return False, "That username already exists."


def get_user_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def authenticate(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if not user or not verify_secret(password, user["password_hash"]):
        return None
    return {"id": user["id"], "username": user["username"]}


def get_security_question(username: str) -> str | None:
    user = get_user_by_username(username)
    return user["security_q"] if user else None


def reset_password(username: str, answer: str, new_password: str) -> tuple[bool, str]:
    user = get_user_by_username(username)
    if not user:
        return False, "User not found."
    if not user["security_a"]:
        return False, "This user has no security question set."
    if not verify_secret(answer.strip().lower(), user["security_a"]):
        return False, "The answer is not correct."
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hash_secret(new_password), username.strip()),
        )
    return True, "Password reset."


def list_users() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, username FROM users ORDER BY username"
        ).fetchall()]


# ── Tasks ──────────────────────────────────────────────────────────────────────

def get_board(user_id: int) -> dict:
    """Owned + globally shared + explicitly-shared tasks, grouped by column."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT t.* FROM tasks t
            LEFT JOIN task_shares ts ON ts.task_id = t.id
            WHERE t.owner_id = ? OR t.is_shared = 1 OR ts.user_id = ?
            ORDER BY t.column_name, t.sort_order ASC, t.id ASC
            """,
            (user_id, user_id),
        ).fetchall()
    board = {c: [] for c in COLUMNS}
    for row in rows:
        d = _task_to_dict(row)
        if d["column_name"] in board:
            board[d["column_name"]].append(d)
    return board


def can_access_task(conn: sqlite3.Connection, task_id: int, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT t.* FROM tasks t
        LEFT JOIN task_shares ts ON ts.task_id = t.id AND ts.user_id = ?
        WHERE t.id = ? AND (t.owner_id = ? OR t.is_shared = 1 OR ts.user_id = ?)
        """,
        (user_id, task_id, user_id, user_id),
    ).fetchone()


def _next_sort_order(conn: sqlite3.Connection, owner_id: int, column: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM tasks WHERE owner_id = ? AND column_name = ?",
        (owner_id, column),
    ).fetchone()
    return row["n"]


def create_task(owner_id: int, data: dict, shared_user_ids: list[int] | None = None) -> int:
    column = data.get("column_name", "ToDo")
    tags = ",".join(data.get("tags", []) or [])
    now = _now()
    with get_connection() as conn:
        order = _next_sort_order(conn, owner_id, column)
        cur = conn.execute(
            """INSERT INTO tasks
               (owner_id, column_name, text, description, priority, tags, due_date,
                is_shared, sort_order, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (owner_id, column, data.get("text", ""), data.get("description", ""),
             data.get("priority", "Medium"), tags, data.get("due_date", ""),
             1 if data.get("is_shared") else 0, order, now, now),
        )
        task_id = cur.lastrowid
        _replace_shares(conn, task_id, shared_user_ids)
        return task_id


def update_task(task_id: int, owner_id: int, data: dict, shared_user_ids: list[int] | None = None) -> bool:
    """Update a task the caller owns. Returns False if not found/not owner."""
    tags = ",".join(data.get("tags", []) or [])
    with get_connection() as conn:
        owned = conn.execute(
            "SELECT id FROM tasks WHERE id = ? AND owner_id = ?", (task_id, owner_id)
        ).fetchone()
        if not owned:
            return False
        conn.execute(
            """UPDATE tasks SET text=?, description=?, priority=?, tags=?, due_date=?,
               is_shared=?, column_name=?, updated_at=? WHERE id=?""",
            (data.get("text", ""), data.get("description", ""), data.get("priority", "Medium"),
             tags, data.get("due_date", ""), 1 if data.get("is_shared") else 0,
             data.get("column_name", "ToDo"), _now(), task_id),
        )
        if shared_user_ids is not None:
            _replace_shares(conn, task_id, shared_user_ids)
    return True


def move_task(task_id: int, user_id: int, new_column: str, new_order: int | None = None) -> bool:
    """Move a task the caller can access to another column/position."""
    if new_column not in COLUMNS:
        return False
    with get_connection() as conn:
        if not can_access_task(conn, task_id, user_id):
            return False
        if new_order is None:
            owner = conn.execute("SELECT owner_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
            new_order = _next_sort_order(conn, owner["owner_id"], new_column)
        conn.execute(
            "UPDATE tasks SET column_name = ?, sort_order = ?, updated_at = ? WHERE id = ?",
            (new_column, new_order, _now(), task_id),
        )
    return True


def reorder_column(user_id: int, column: str, ordered_ids: list[int]) -> bool:
    """Persist a new within-column order (drag & drop). Only affects accessible tasks."""
    if column not in COLUMNS:
        return False
    with get_connection() as conn:
        for position, tid in enumerate(ordered_ids):
            if can_access_task(conn, tid, user_id):
                conn.execute(
                    "UPDATE tasks SET column_name = ?, sort_order = ?, updated_at = ? WHERE id = ?",
                    (column, position, _now(), tid),
                )
    return True


def delete_task(task_id: int, owner_id: int) -> bool:
    """Only the owner may delete. Returns False otherwise."""
    with get_connection() as conn:
        owned = conn.execute(
            "SELECT id FROM tasks WHERE id = ? AND owner_id = ?", (task_id, owner_id)
        ).fetchone()
        if not owned:
            return False
        conn.execute("DELETE FROM task_shares WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return True


def get_shared_user_ids(task_id: int) -> list[int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT user_id FROM task_shares WHERE task_id = ?", (task_id,)).fetchall()
    return [r["user_id"] for r in rows]


def _replace_shares(conn: sqlite3.Connection, task_id: int, user_ids: list[int] | None) -> None:
    if user_ids is None:
        return
    conn.execute("DELETE FROM task_shares WHERE task_id = ?", (task_id,))
    for uid in user_ids:
        try:
            conn.execute("INSERT INTO task_shares (task_id, user_id) VALUES (?,?)", (task_id, uid))
        except sqlite3.IntegrityError:
            pass
