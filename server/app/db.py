"""
db.py - SQLite persistence layer for the Kanbanpy Pro backend.

WAL mode so the PWA and desktop client don't block each other. Data model:
  * boards          — multiple boards per user, shareable (owner / global / members)
  * board_members   — explicit per-user board sharing
  * tasks           — belong to a board, can be archived
  * activity_log    — per-board history of what happened
  * task_shares     — legacy per-task sharing (kept for migration, unused in queries)
"""
import calendar
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone

from .config import settings
from .security import hash_secret, verify_secret

COLUMNS = ("ToDo", "Doing", "Done")
DEFAULT_BOARD_NAME = "Mi tablero"


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


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


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

            CREATE TABLE IF NOT EXISTS boards (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id    INTEGER NOT NULL,
                name        TEXT    NOT NULL,
                color       TEXT    DEFAULT '#5b8cff',
                is_shared   INTEGER DEFAULT 0,
                position    INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT '',
                FOREIGN KEY(owner_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS board_members (
                board_id  INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                PRIMARY KEY (board_id, user_id),
                FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id     INTEGER NOT NULL,
                board_id     INTEGER,
                column_name  TEXT    NOT NULL DEFAULT 'ToDo',
                text         TEXT    NOT NULL,
                description  TEXT    DEFAULT '',
                priority     TEXT    DEFAULT 'Medium',
                tags         TEXT    DEFAULT '',
                due_date     TEXT    DEFAULT '',
                recurrence   TEXT    DEFAULT '',
                is_shared    INTEGER DEFAULT 0,
                assignee_id  INTEGER,
                sort_order   INTEGER DEFAULT 0,
                archived     INTEGER DEFAULT 0,
                archived_at  TEXT    DEFAULT '',
                reminded_on  TEXT    DEFAULT '',
                created_at   TEXT    DEFAULT '',
                updated_at   TEXT    DEFAULT '',
                FOREIGN KEY(owner_id) REFERENCES users(id),
                FOREIGN KEY(board_id) REFERENCES boards(id)
            );

            CREATE TABLE IF NOT EXISTS task_shares (
                task_id  INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                PRIMARY KEY (task_id, user_id),
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id    INTEGER NOT NULL,
                task_id     INTEGER,
                user_id     INTEGER NOT NULL,
                action      TEXT    NOT NULL,
                detail      TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT '',
                FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS subtasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     INTEGER NOT NULL,
                text        TEXT    NOT NULL,
                done        INTEGER DEFAULT 0,
                position    INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT '',
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS comments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                body        TEXT    NOT NULL,
                created_at  TEXT    DEFAULT '',
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS push_subscriptions (
                endpoint    TEXT PRIMARY KEY,
                user_id     INTEGER NOT NULL,
                data        TEXT NOT NULL,
                created_at  TEXT DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_members_user ON board_members(user_id);
            CREATE INDEX IF NOT EXISTS idx_activity_board ON activity_log(board_id);
            CREATE INDEX IF NOT EXISTS idx_push_user ON push_subscriptions(user_id);
            CREATE INDEX IF NOT EXISTS idx_subtasks_task ON subtasks(task_id);
            CREATE INDEX IF NOT EXISTS idx_comments_task ON comments(task_id);
            """
        )
        # Migrate older schemas that predate boards/archiving. This must run
        # before any index that references the new columns.
        tcols = _columns(conn, "tasks")
        for col, ddl in [
            ("board_id", "ALTER TABLE tasks ADD COLUMN board_id INTEGER"),
            ("archived", "ALTER TABLE tasks ADD COLUMN archived INTEGER DEFAULT 0"),
            ("archived_at", "ALTER TABLE tasks ADD COLUMN archived_at TEXT DEFAULT ''"),
            ("assignee_id", "ALTER TABLE tasks ADD COLUMN assignee_id INTEGER"),
            ("reminded_on", "ALTER TABLE tasks ADD COLUMN reminded_on TEXT DEFAULT ''"),
            ("recurrence", "ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT ''"),
        ]:
            if col not in tcols:
                conn.execute(ddl)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_board ON tasks(board_id)")
        _migrate_orphan_tasks(conn)


def _migrate_orphan_tasks(conn: sqlite3.Connection) -> None:
    """Give every user a default board and move board-less tasks onto it."""
    owners = conn.execute(
        "SELECT DISTINCT owner_id FROM tasks WHERE board_id IS NULL"
    ).fetchall()
    for row in owners:
        owner_id = row["owner_id"]
        board = conn.execute(
            "SELECT id FROM boards WHERE owner_id = ? ORDER BY position, id LIMIT 1",
            (owner_id,),
        ).fetchone()
        if board is None:
            cur = conn.execute(
                "INSERT INTO boards (owner_id, name, position, created_at) VALUES (?,?,?,?)",
                (owner_id, DEFAULT_BOARD_NAME, 0, _now()),
            )
            board_id = cur.lastrowid
        else:
            board_id = board["id"]
        # If any legacy task was globally shared, keep the board shared too.
        shared = conn.execute(
            "SELECT MAX(is_shared) AS s FROM tasks WHERE owner_id = ? AND board_id IS NULL",
            (owner_id,),
        ).fetchone()["s"]
        if shared:
            conn.execute("UPDATE boards SET is_shared = 1 WHERE id = ?", (board_id,))
        conn.execute(
            "UPDATE tasks SET board_id = ? WHERE owner_id = ? AND board_id IS NULL",
            (board_id, owner_id),
        )


# ── Row helpers ────────────────────────────────────────────────────────────────

def _task_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = [t for t in (d.get("tags") or "").split(",") if t]
    d["is_shared"] = bool(d.get("is_shared", 0))
    d["archived"] = bool(d.get("archived", 0))
    return d


# ── Users ────────────────────────────────────────────────────────────────────

def create_user(username: str, password: str, security_q: str = "", security_a: str = "") -> tuple[bool, str]:
    username = username.strip()
    if not username or not password:
        return False, "Username and password cannot be empty."
    answer_hash = hash_secret(security_a.strip().lower()) if security_a.strip() else ""
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, security_q, security_a, created_at) "
                "VALUES (?,?,?,?,?)",
                (username, hash_secret(password), security_q.strip(), answer_hash, _now()),
            )
            # Every new user starts with a default board.
            conn.execute(
                "INSERT INTO boards (owner_id, name, position, created_at) VALUES (?,?,?,?)",
                (cur.lastrowid, DEFAULT_BOARD_NAME, 0, _now()),
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


# ── Boards ─────────────────────────────────────────────────────────────────────

def _board_access(conn: sqlite3.Connection, board_id: int, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT b.* FROM boards b
        LEFT JOIN board_members m ON m.board_id = b.id AND m.user_id = ?
        WHERE b.id = ? AND (b.owner_id = ? OR b.is_shared = 1 OR m.user_id = ?)
        """,
        (user_id, board_id, user_id, user_id),
    ).fetchone()


def ensure_default_board(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM boards WHERE owner_id = ? ORDER BY position, id LIMIT 1", (user_id,)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO boards (owner_id, name, position, created_at) VALUES (?,?,?,?)",
            (user_id, DEFAULT_BOARD_NAME, 0, _now()),
        )
        return cur.lastrowid


def list_boards(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT b.*, (b.owner_id = ?) AS is_owner FROM boards b
            LEFT JOIN board_members m ON m.board_id = b.id
            WHERE b.owner_id = ? OR b.is_shared = 1 OR m.user_id = ?
            ORDER BY b.position, b.id
            """,
            (user_id, user_id, user_id),
        ).fetchall()
    boards = []
    for r in rows:
        d = dict(r)
        d["is_shared"] = bool(d["is_shared"])
        d["is_owner"] = bool(d["is_owner"])
        boards.append(d)
    return boards


def create_board(owner_id: int, name: str, color: str = "#5b8cff") -> int:
    name = (name or "").strip() or "Nuevo tablero"
    with get_connection() as conn:
        pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS n FROM boards WHERE owner_id = ?", (owner_id,)
        ).fetchone()["n"]
        cur = conn.execute(
            "INSERT INTO boards (owner_id, name, color, position, created_at) VALUES (?,?,?,?,?)",
            (owner_id, name, color, pos, _now()),
        )
        return cur.lastrowid


def update_board(board_id: int, owner_id: int, name: str | None, color: str | None,
                 is_shared: bool | None, member_ids: list[int] | None) -> bool:
    with get_connection() as conn:
        owned = conn.execute(
            "SELECT id FROM boards WHERE id = ? AND owner_id = ?", (board_id, owner_id)
        ).fetchone()
        if not owned:
            return False
        if name is not None:
            conn.execute("UPDATE boards SET name = ? WHERE id = ?", (name.strip(), board_id))
        if color is not None:
            conn.execute("UPDATE boards SET color = ? WHERE id = ?", (color, board_id))
        if is_shared is not None:
            conn.execute("UPDATE boards SET is_shared = ? WHERE id = ?", (1 if is_shared else 0, board_id))
        if member_ids is not None:
            conn.execute("DELETE FROM board_members WHERE board_id = ?", (board_id,))
            for uid in member_ids:
                try:
                    conn.execute("INSERT INTO board_members (board_id, user_id) VALUES (?,?)", (board_id, uid))
                except sqlite3.IntegrityError:
                    pass
    return True


def delete_board(board_id: int, owner_id: int) -> bool:
    with get_connection() as conn:
        owned = conn.execute(
            "SELECT id FROM boards WHERE id = ? AND owner_id = ?", (board_id, owner_id)
        ).fetchone()
        if not owned:
            return False
        conn.execute("DELETE FROM tasks WHERE board_id = ?", (board_id,))
        conn.execute("DELETE FROM board_members WHERE board_id = ?", (board_id,))
        conn.execute("DELETE FROM activity_log WHERE board_id = ?", (board_id,))
        conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    return True


def get_board_members(board_id: int) -> list[int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT user_id FROM board_members WHERE board_id = ?", (board_id,)).fetchall()
    return [r["user_id"] for r in rows]


# ── Activity log ─────────────────────────────────────────────────────────────

def _log(conn: sqlite3.Connection, board_id: int, task_id: int | None, user_id: int,
         action: str, detail: str = "") -> None:
    conn.execute(
        "INSERT INTO activity_log (board_id, task_id, user_id, action, detail, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (board_id, task_id, user_id, action, detail, _now()),
    )


def get_activity(board_id: int, user_id: int, limit: int = 50) -> list[dict] | None:
    with get_connection() as conn:
        if not _board_access(conn, board_id, user_id):
            return None
        rows = conn.execute(
            """
            SELECT a.action, a.detail, a.created_at, u.username
            FROM activity_log a JOIN users u ON u.id = a.user_id
            WHERE a.board_id = ? ORDER BY a.id DESC LIMIT ?
            """,
            (board_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Tasks ──────────────────────────────────────────────────────────────────────

def get_board_tasks(user_id: int, board_id: int, archived: bool = False) -> dict | None:
    """Grouped active (or archived) tasks for a board the user can access."""
    with get_connection() as conn:
        if not _board_access(conn, board_id, user_id):
            return None
        rows = conn.execute(
            """
            SELECT t.*, u.username AS assignee_username,
                   (SELECT COUNT(*) FROM subtasks s WHERE s.task_id = t.id) AS subtask_total,
                   (SELECT COUNT(*) FROM subtasks s WHERE s.task_id = t.id AND s.done = 1) AS subtask_done,
                   (SELECT COUNT(*) FROM comments c WHERE c.task_id = t.id) AS comment_count
            FROM tasks t LEFT JOIN users u ON u.id = t.assignee_id
            WHERE t.board_id = ? AND t.archived = ?
            ORDER BY t.column_name, t.sort_order ASC, t.id ASC
            """,
            (board_id, 1 if archived else 0),
        ).fetchall()
    if archived:
        return {"archived": [_task_to_dict(r) for r in rows]}
    board = {c: [] for c in COLUMNS}
    for row in rows:
        d = _task_to_dict(row)
        if d["column_name"] in board:
            board[d["column_name"]].append(d)
    return board


def _accessible_task(conn: sqlite3.Connection, task_id: int, user_id: int) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row or row["board_id"] is None:
        return None
    return row if _board_access(conn, row["board_id"], user_id) else None


def _next_sort_order(conn: sqlite3.Connection, board_id: int, column: str) -> int:
    return conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM tasks "
        "WHERE board_id = ? AND column_name = ? AND archived = 0",
        (board_id, column),
    ).fetchone()["n"]


def create_task(owner_id: int, board_id: int, data: dict) -> int | None:
    column = data.get("column_name", "ToDo")
    tags = ",".join(data.get("tags", []) or [])
    now = _now()
    with get_connection() as conn:
        if not _board_access(conn, board_id, owner_id):
            return None
        order = _next_sort_order(conn, board_id, column)
        cur = conn.execute(
            """INSERT INTO tasks
               (owner_id, board_id, column_name, text, description, priority, tags, due_date,
                recurrence, assignee_id, sort_order, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (owner_id, board_id, column, data.get("text", ""), data.get("description", ""),
             data.get("priority", "Medium"), tags, data.get("due_date", ""),
             data.get("recurrence", ""), data.get("assignee_id"), order, now, now),
        )
        task_id = cur.lastrowid
        _log(conn, board_id, task_id, owner_id, "created", data.get("text", ""))
        return task_id


def update_task(task_id: int, user_id: int, data: dict) -> bool:
    """Any board member may edit a task's content."""
    tags = ",".join(data.get("tags", []) or [])
    with get_connection() as conn:
        task = _accessible_task(conn, task_id, user_id)
        if not task:
            return False
        conn.execute(
            """UPDATE tasks SET text=?, description=?, priority=?, tags=?, due_date=?,
               recurrence=?, column_name=?, assignee_id=?, updated_at=? WHERE id=?""",
            (data.get("text", ""), data.get("description", ""), data.get("priority", "Medium"),
             tags, data.get("due_date", ""), data.get("recurrence", ""),
             data.get("column_name", task["column_name"]), data.get("assignee_id"), _now(), task_id),
        )
        _log(conn, task["board_id"], task_id, user_id, "edited", data.get("text", ""))
    return True


def _advance_date(date_str: str, rule: str) -> str | None:
    try:
        y, m, d = (int(x) for x in date_str.split("-"))
        base = date(y, m, d)
    except (ValueError, AttributeError):
        return None
    if rule == "daily":
        from datetime import timedelta
        return (base + timedelta(days=1)).isoformat()
    if rule == "weekly":
        from datetime import timedelta
        return (base + timedelta(days=7)).isoformat()
    if rule == "monthly":
        nm, ny = (1, y + 1) if m == 12 else (m + 1, y)
        return date(ny, nm, min(d, calendar.monthrange(ny, nm)[1])).isoformat()
    return None


def move_task(task_id: int, user_id: int, new_column: str, new_order: int | None = None) -> bool:
    if new_column not in COLUMNS:
        return False
    with get_connection() as conn:
        task = _accessible_task(conn, task_id, user_id)
        if not task:
            return False
        if new_order is None:
            new_order = _next_sort_order(conn, task["board_id"], new_column)
        conn.execute(
            "UPDATE tasks SET column_name = ?, sort_order = ?, updated_at = ? WHERE id = ?",
            (new_column, new_order, _now(), task_id),
        )
        if new_column != task["column_name"]:
            _log(conn, task["board_id"], task_id, user_id, "moved", new_column)
        # Recurring task completed → spawn the next occurrence.
        if (new_column == "Done" and task["column_name"] != "Done"
                and task["recurrence"] and task["due_date"]):
            nxt = _advance_date(task["due_date"], task["recurrence"])
            if nxt:
                order = _next_sort_order(conn, task["board_id"], "ToDo")
                now = _now()
                cur = conn.execute(
                    """INSERT INTO tasks
                       (owner_id, board_id, column_name, text, description, priority, tags,
                        due_date, recurrence, assignee_id, sort_order, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (task["owner_id"], task["board_id"], "ToDo", task["text"], task["description"],
                     task["priority"], task["tags"], nxt, task["recurrence"], task["assignee_id"],
                     order, now, now),
                )
                _log(conn, task["board_id"], cur.lastrowid, user_id, "created", task["text"])
    return True


def reorder_column(user_id: int, board_id: int, column: str, ordered_ids: list[int]) -> bool:
    if column not in COLUMNS:
        return False
    with get_connection() as conn:
        if not _board_access(conn, board_id, user_id):
            return False
        for position, tid in enumerate(ordered_ids):
            conn.execute(
                "UPDATE tasks SET column_name = ?, sort_order = ?, updated_at = ? "
                "WHERE id = ? AND board_id = ?",
                (column, position, _now(), tid, board_id),
            )
    return True


def set_archived(task_id: int, user_id: int, archived: bool) -> bool:
    with get_connection() as conn:
        task = _accessible_task(conn, task_id, user_id)
        if not task:
            return False
        conn.execute(
            "UPDATE tasks SET archived = ?, archived_at = ?, updated_at = ? WHERE id = ?",
            (1 if archived else 0, _now() if archived else "", _now(), task_id),
        )
        _log(conn, task["board_id"], task_id, user_id,
             "archived" if archived else "restored", task["text"])
    return True


def delete_task(task_id: int, user_id: int) -> bool:
    """The task owner or the board owner may delete."""
    with get_connection() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task or task["board_id"] is None:
            return False
        board = _board_access(conn, task["board_id"], user_id)
        if not board:
            return False
        if task["owner_id"] != user_id and board["owner_id"] != user_id:
            return False
        conn.execute("DELETE FROM task_shares WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        _log(conn, task["board_id"], None, user_id, "deleted", task["text"])
    return True


# ── Push subscriptions ─────────────────────────────────────────────────────────

def save_push_subscription(user_id: int, endpoint: str, data_json: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO push_subscriptions (endpoint, user_id, data, created_at) VALUES (?,?,?,?) "
            "ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id, data=excluded.data",
            (endpoint, user_id, data_json, _now()),
        )


def delete_push_subscription(endpoint: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))


def get_subscriptions_for_users(user_ids: list[int]) -> list[dict]:
    if not user_ids:
        return []
    placeholders = ",".join("?" * len(user_ids))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT endpoint, data FROM push_subscriptions WHERE user_id IN ({placeholders})",
            user_ids,
        ).fetchall()
    return [dict(r) for r in rows]


# ── Task detail: subtasks, comments, per-task activity ──────────────────────────

def get_task_detail(task_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        task = _accessible_task(conn, task_id, user_id)
        if not task:
            return None
        detail = _task_to_dict(task)
        detail["subtasks"] = [dict(r) | {"done": bool(r["done"])} for r in conn.execute(
            "SELECT id, text, done, position FROM subtasks WHERE task_id = ? ORDER BY position, id",
            (task_id,)).fetchall()]
        detail["comments"] = [dict(r) for r in conn.execute(
            "SELECT c.id, c.body, c.created_at, u.username FROM comments c "
            "JOIN users u ON u.id = c.user_id WHERE c.task_id = ? ORDER BY c.id",
            (task_id,)).fetchall()]
        detail["activity"] = [dict(r) for r in conn.execute(
            "SELECT a.action, a.detail, a.created_at, u.username FROM activity_log a "
            "JOIN users u ON u.id = a.user_id WHERE a.task_id = ? ORDER BY a.id DESC LIMIT 30",
            (task_id,)).fetchall()]
    return detail


def _access_via_task(conn, task_id, user_id):
    return _accessible_task(conn, task_id, user_id)


def add_subtask(task_id: int, user_id: int, text: str) -> int | None:
    with get_connection() as conn:
        if not _accessible_task(conn, task_id, user_id):
            return None
        pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS n FROM subtasks WHERE task_id = ?", (task_id,)
        ).fetchone()["n"]
        cur = conn.execute(
            "INSERT INTO subtasks (task_id, text, position, created_at) VALUES (?,?,?,?)",
            (task_id, text.strip(), pos, _now()),
        )
        return cur.lastrowid


def update_subtask(subtask_id: int, user_id: int, text: str | None, done: bool | None) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT task_id FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
        if not row or not _accessible_task(conn, row["task_id"], user_id):
            return False
        if text is not None:
            conn.execute("UPDATE subtasks SET text = ? WHERE id = ?", (text.strip(), subtask_id))
        if done is not None:
            conn.execute("UPDATE subtasks SET done = ? WHERE id = ?", (1 if done else 0, subtask_id))
    return True


def delete_subtask(subtask_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT task_id FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
        if not row or not _accessible_task(conn, row["task_id"], user_id):
            return False
        conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
    return True


def add_comment(task_id: int, user_id: int, body: str) -> int | None:
    body = body.strip()
    if not body:
        return None
    with get_connection() as conn:
        if not _accessible_task(conn, task_id, user_id):
            return None
        cur = conn.execute(
            "INSERT INTO comments (task_id, user_id, body, created_at) VALUES (?,?,?,?)",
            (task_id, user_id, body, _now()),
        )
        return cur.lastrowid


def delete_comment(comment_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT c.user_id, t.board_id FROM comments c JOIN tasks t ON t.id = c.task_id "
            "WHERE c.id = ?", (comment_id,)).fetchone()
        if not row:
            return False
        board = _board_access(conn, row["board_id"], user_id) if row["board_id"] else None
        if not board:
            return False
        if row["user_id"] != user_id and board["owner_id"] != user_id:
            return False
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    return True


# ── Due-date reminders ─────────────────────────────────────────────────────────

def due_tasks(date_str: str) -> list[dict]:
    """Unfinished, non-archived tasks due on date_str not yet reminded for it."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, board_id, assignee_id, text FROM tasks
               WHERE due_date = ? AND archived = 0 AND column_name != 'Done'
                 AND COALESCE(reminded_on, '') != ?""",
            (date_str, date_str),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_reminded(task_id: int, date_str: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE tasks SET reminded_on = ? WHERE id = ?", (date_str, task_id))


def board_notify_user_ids(board_id: int, exclude: int | None = None) -> list[int]:
    """Users who should be notified about a board: owner + members (+ everyone if shared)."""
    with get_connection() as conn:
        board = conn.execute("SELECT owner_id, is_shared FROM boards WHERE id = ?", (board_id,)).fetchone()
        if not board:
            return []
        if board["is_shared"]:
            ids = {r["id"] for r in conn.execute("SELECT id FROM users").fetchall()}
        else:
            ids = {board["owner_id"]}
            ids.update(r["user_id"] for r in conn.execute(
                "SELECT user_id FROM board_members WHERE board_id = ?", (board_id,)).fetchall())
    ids.discard(exclude)
    return list(ids)
