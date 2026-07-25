"""
db.py - Postgres persistence layer for the Kanbanpy Pro backend.

Connects to the shared postgres-shared container (see
/srv/docker/postgres-shared/docker-compose.yml) via DATABASE_URL. Data model:
  * boards          — multiple boards per user, shareable (owner / global / members)
  * board_members   — explicit per-user board sharing
  * tasks           — belong to a board, can be archived
  * activity_log    — per-board history of what happened
  * task_shares     — legacy per-task sharing (kept for migration, unused in queries)
"""
import calendar
import os
import secrets
from contextlib import contextmanager
from datetime import date, datetime, timezone

import psycopg2
import psycopg2.extras

from .security import hash_secret, verify_secret

# Unambiguous alphabet for invite codes (no 0/O/1/I) — meant to be read aloud
# or typed by hand.
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

COLUMNS = ("Backlog", "ToDo", "Doing", "Done")
DEFAULT_BOARD_NAME = "Mi tablero"

# No SQLite fallback: this app is Postgres-only. Fail loudly and immediately
# if the orchestrating environment forgot to inject the connection string,
# rather than letting a confusing psycopg2 error surface deep inside init_db().
try:
    DATABASE_URL = os.environ["DATABASE_URL"]
except KeyError:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. Kanbanpy requires a "
        "Postgres connection string, e.g. postgresql://user:pass@host:5432/dbname"
    )


class PGConnection:
    """Thin sqlite3.Connection-like wrapper around a psycopg2 connection.

    sqlite3.Connection has a built-in `.execute(sql, params)` shorthand that
    implicitly creates a cursor, runs the query, and returns that cursor so
    callers can chain `.fetchone()` / `.fetchall()` directly. psycopg2 has no
    such shorthand — you must always go through `.cursor()` first. This
    wrapper restores that convenience so the rest of this file (written
    against sqlite3's API) needed only placeholder (`?` -> `%s`) and
    id-generation (`lastrowid` -> `RETURNING id`) changes, not a full rewrite.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        cur.execute(sql, params if params else None)
        return cur

    def executescript(self, sql):
        cur = self._conn.cursor()
        cur.execute(sql)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(*args, **kwargs)


def _new_db_connection():
    """Open a new Postgres connection.

    Session timezone pinned to UTC so `now()` matches the UTC ISO-8601
    strings `_now()` used to produce with SQLite. `cursor_factory` defaults
    to RealDictCursor so every `.cursor()` call returns dict-like rows
    (`row['col']`), matching the `sqlite3.Row` access pattern used
    throughout this file.
    """
    conn = psycopg2.connect(DATABASE_URL, options="-c timezone=UTC")
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return PGConnection(conn)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_connection():
    conn = _new_db_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id           SERIAL PRIMARY KEY,
                name         TEXT NOT NULL,
                invite_code  TEXT NOT NULL UNIQUE,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS users (
                id             SERIAL PRIMARY KEY,
                username       TEXT    NOT NULL UNIQUE,
                password_hash  TEXT    NOT NULL,
                security_q     TEXT    DEFAULT '',
                security_a     TEXT    DEFAULT '',
                org_id         INTEGER REFERENCES organizations(id),
                is_org_admin   BOOLEAN NOT NULL DEFAULT FALSE,
                is_active      BOOLEAN NOT NULL DEFAULT TRUE,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS boards (
                id          SERIAL PRIMARY KEY,
                owner_id    INTEGER NOT NULL REFERENCES users(id),
                org_id      INTEGER REFERENCES organizations(id),
                name        TEXT    NOT NULL,
                color       TEXT    DEFAULT '#5b8cff',
                is_shared   INTEGER DEFAULT 0,
                position    INTEGER DEFAULT 0,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS board_members (
                board_id  INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                user_id   INTEGER NOT NULL REFERENCES users(id),
                PRIMARY KEY (board_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id           SERIAL PRIMARY KEY,
                owner_id     INTEGER NOT NULL REFERENCES users(id),
                board_id     INTEGER REFERENCES boards(id),
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
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS task_shares (
                task_id  INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                user_id  INTEGER NOT NULL REFERENCES users(id),
                PRIMARY KEY (task_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id          SERIAL PRIMARY KEY,
                board_id    INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                task_id     INTEGER,
                user_id     INTEGER NOT NULL,
                action      TEXT    NOT NULL,
                detail      TEXT    DEFAULT '',
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS subtasks (
                id          SERIAL PRIMARY KEY,
                task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                text        TEXT    NOT NULL,
                done        INTEGER DEFAULT 0,
                position    INTEGER DEFAULT 0,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS comments (
                id          SERIAL PRIMARY KEY,
                task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                body        TEXT    NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS push_subscriptions (
                endpoint    TEXT PRIMARY KEY,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                data        TEXT NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS settings (
                org_id  INTEGER REFERENCES organizations(id),
                key     TEXT NOT NULL,
                value   TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_members_user ON board_members(user_id);
            CREATE INDEX IF NOT EXISTS idx_activity_board ON activity_log(board_id);
            CREATE INDEX IF NOT EXISTS idx_push_user ON push_subscriptions(user_id);
            CREATE INDEX IF NOT EXISTS idx_subtasks_task ON subtasks(task_id);
            CREATE INDEX IF NOT EXISTS idx_comments_task ON comments(task_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_board ON tasks(board_id);

            -- CREATE TABLE IF NOT EXISTS is a no-op on tables that already
            -- existed before organizations were introduced (Phase A), so the
            -- org_id/is_org_admin columns above never land on them without
            -- these explicit ALTERs.
            ALTER TABLE users ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(id);
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_org_admin BOOLEAN NOT NULL DEFAULT FALSE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
            ALTER TABLE boards ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(id);
            ALTER TABLE settings ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(id);

            CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
            CREATE INDEX IF NOT EXISTS idx_boards_org ON boards(org_id);
            """
        )
        _migrate_orphan_tasks(conn)
        _bootstrap_default_org(conn)
        conn.executescript(
            """
            ALTER TABLE users ALTER COLUMN org_id SET NOT NULL;
            ALTER TABLE boards ALTER COLUMN org_id SET NOT NULL;
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'settings_pkey' AND conrelid = 'settings'::regclass
                ) THEN
                    ALTER TABLE settings DROP CONSTRAINT settings_pkey;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'settings_pkey' AND conrelid = 'settings'::regclass
                ) THEN
                    ALTER TABLE settings ADD CONSTRAINT settings_pkey PRIMARY KEY (org_id, key);
                END IF;
            END $$;
            """
        )


def _generate_invite_code(conn) -> str:
    """A short, human-shareable code (no ambiguous characters), unique among orgs."""
    while True:
        code = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))
        exists = conn.execute(
            "SELECT 1 FROM organizations WHERE invite_code = %s", (code,)
        ).fetchone()
        if not exists:
            return code


def _bootstrap_default_org(conn) -> None:
    """Fold any pre-organizations users/boards (from before this feature existed)
    into one default org, so existing accounts keep working unmodified. The
    lowest-id user becomes that org's admin, mirroring the old instance-wide
    "first user is admin" rule this replaces. No-op once every user has an org.
    """
    orphans = conn.execute(
        "SELECT id FROM users WHERE org_id IS NULL ORDER BY id"
    ).fetchall()
    if not orphans:
        return
    cur = conn.execute(
        "INSERT INTO organizations (name, invite_code, created_at) VALUES (%s,%s,%s) RETURNING id",
        ("Mi organización", _generate_invite_code(conn), _now()),
    )
    org_id = cur.fetchone()["id"]
    admin_id = orphans[0]["id"]
    for row in orphans:
        conn.execute(
            "UPDATE users SET org_id = %s, is_org_admin = %s WHERE id = %s",
            (org_id, row["id"] == admin_id, row["id"]),
        )
    conn.execute("UPDATE boards SET org_id = %s WHERE org_id IS NULL", (org_id,))


def _migrate_orphan_tasks(conn) -> None:
    """Give every user a default board and move board-less tasks onto it."""
    owners = conn.execute(
        "SELECT DISTINCT owner_id FROM tasks WHERE board_id IS NULL"
    ).fetchall()
    for row in owners:
        owner_id = row["owner_id"]
        board = conn.execute(
            "SELECT id FROM boards WHERE owner_id = %s ORDER BY position, id LIMIT 1",
            (owner_id,),
        ).fetchone()
        if board is None:
            cur = conn.execute(
                "INSERT INTO boards (owner_id, name, position, created_at) VALUES (%s,%s,%s,%s) RETURNING id",
                (owner_id, DEFAULT_BOARD_NAME, 0, _now()),
            )
            board_id = cur.fetchone()["id"]
        else:
            board_id = board["id"]
        # If any legacy task was globally shared, keep the board shared too.
        shared = conn.execute(
            "SELECT MAX(is_shared) AS s FROM tasks WHERE owner_id = %s AND board_id IS NULL",
            (owner_id,),
        ).fetchone()["s"]
        if shared:
            conn.execute("UPDATE boards SET is_shared = 1 WHERE id = %s", (board_id,))
        conn.execute(
            "UPDATE tasks SET board_id = %s WHERE owner_id = %s AND board_id IS NULL",
            (board_id, owner_id),
        )


# ── Row helpers ────────────────────────────────────────────────────────────────

def _task_to_dict(row) -> dict:
    d = dict(row)
    d["tags"] = [t for t in (d.get("tags") or "").split(",") if t]
    d["is_shared"] = bool(d.get("is_shared", 0))
    d["archived"] = bool(d.get("archived", 0))
    return d


# ── Users ────────────────────────────────────────────────────────────────────

def create_user(username: str, password: str, security_q: str = "", security_a: str = "",
                org_mode: str = "create", org_name: str = "", invite_code: str = "") -> tuple[bool, str]:
    username = username.strip()
    if not username or not password:
        return False, "Username and password cannot be empty."
    answer_hash = hash_secret(security_a.strip().lower()) if security_a.strip() else ""
    try:
        with get_connection() as conn:
            if org_mode == "join":
                org = conn.execute(
                    "SELECT id FROM organizations WHERE invite_code = %s",
                    (invite_code.strip().upper(),),
                ).fetchone()
                if not org:
                    return False, "Invalid invite code."
                org_id = org["id"]
                is_org_admin = False
            else:
                cur = conn.execute(
                    "INSERT INTO organizations (name, invite_code, created_at) VALUES (%s,%s,%s) RETURNING id",
                    (org_name.strip() or f"{username}'s organization", _generate_invite_code(conn), _now()),
                )
                org_id = cur.fetchone()["id"]
                is_org_admin = True

            cur = conn.execute(
                "INSERT INTO users (username, password_hash, security_q, security_a, org_id, is_org_admin, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (username, hash_secret(password), security_q.strip(), answer_hash, org_id, is_org_admin, _now()),
            )
            user_id = cur.fetchone()["id"]
            # Every new user starts with a default board.
            conn.execute(
                "INSERT INTO boards (owner_id, org_id, name, position, created_at) VALUES (%s,%s,%s,%s,%s)",
                (user_id, org_id, DEFAULT_BOARD_NAME, 0, _now()),
            )
        return True, "User registered."
    except psycopg2.IntegrityError:
        return False, "That username already exists."


def get_user_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = %s", (username.strip(),)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT u.id, u.username, u.org_id, u.is_org_admin, u.is_active, o.name AS org_name "
            "FROM users u LEFT JOIN organizations o ON o.id = u.org_id WHERE u.id = %s",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def authenticate(username: str, password: str) -> dict | None:
    """Return the user on success, or None. Inactive accounts authenticate as
    None so callers that only care about success/failure stay simple; use
    login_user() when you need a distinct 'deactivated' error."""
    user, _reason = login_user(username, password)
    return user


def login_user(username: str, password: str) -> tuple[dict | None, str]:
    """Validate credentials. Returns (user, "") on success, or (None, reason)
    where reason is "invalid" or "inactive"."""
    user = get_user_by_username(username)
    if not user or not verify_secret(password, user["password_hash"]):
        return None, "invalid"
    if not user.get("is_active", True):
        return None, "inactive"
    return get_user_by_id(user["id"]), ""


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
            "UPDATE users SET password_hash = %s WHERE username = %s",
            (hash_secret(new_password), username.strip()),
        )
    return True, "Password reset."


def list_users(org_id: int) -> list[dict]:
    """Active org members — used for assignee / share pickers."""
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, username FROM users WHERE org_id = %s AND is_active = TRUE ORDER BY username",
            (org_id,),
        ).fetchall()]


# ── Organization admin ─────────────────────────────────────────────────────────

def get_organization(org_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, invite_code, created_at FROM organizations WHERE id = %s",
            (org_id,),
        ).fetchone()
    return dict(row) if row else None


def rename_organization(org_id: int, name: str) -> bool:
    name = name.strip()
    if not name:
        return False
    with get_connection() as conn:
        conn.execute("UPDATE organizations SET name = %s WHERE id = %s", (name, org_id))
    return True


def rotate_invite_code(org_id: int) -> str | None:
    with get_connection() as conn:
        code = _generate_invite_code(conn)
        cur = conn.execute(
            "UPDATE organizations SET invite_code = %s WHERE id = %s RETURNING invite_code",
            (code, org_id),
        )
        row = cur.fetchone()
    return row["invite_code"] if row else None


def list_org_members(org_id: int) -> list[dict]:
    """All members (active and inactive) for the org admin panel."""
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            """
            SELECT id, username, is_org_admin, is_active, created_at
            FROM users WHERE org_id = %s
            ORDER BY is_org_admin DESC, username
            """,
            (org_id,),
        ).fetchall()]


def set_member_active(org_id: int, member_id: int, active: bool, actor_id: int) -> tuple[bool, str]:
    """Activate/deactivate a member of the same org. Admins can't deactivate themselves."""
    if member_id == actor_id and not active:
        return False, "You cannot deactivate your own account."
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, org_id FROM users WHERE id = %s", (member_id,)
        ).fetchone()
        if not row or row["org_id"] != org_id:
            return False, "User not found in this organization."
        conn.execute(
            "UPDATE users SET is_active = %s WHERE id = %s", (active, member_id)
        )
    return True, "Updated."


# ── Boards ─────────────────────────────────────────────────────────────────────

def _board_access(conn, board_id: int, user_id: int, org_id: int):
    return conn.execute(
        """
        SELECT b.* FROM boards b
        LEFT JOIN board_members m ON m.board_id = b.id AND m.user_id = %s
        WHERE b.id = %s AND b.org_id = %s AND (b.owner_id = %s OR b.is_shared = 1 OR m.user_id = %s)
        """,
        (user_id, board_id, org_id, user_id, user_id),
    ).fetchone()


def ensure_default_board(user_id: int, org_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM boards WHERE owner_id = %s ORDER BY position, id LIMIT 1", (user_id,)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO boards (owner_id, org_id, name, position, created_at) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (user_id, org_id, DEFAULT_BOARD_NAME, 0, _now()),
        )
        return cur.fetchone()["id"]


def list_boards(user_id: int, org_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT b.*, (b.owner_id = %s) AS is_owner FROM boards b
            LEFT JOIN board_members m ON m.board_id = b.id
            WHERE b.org_id = %s AND (b.owner_id = %s OR b.is_shared = 1 OR m.user_id = %s)
            ORDER BY b.position, b.id
            """,
            (user_id, org_id, user_id, user_id),
        ).fetchall()
    boards = []
    for r in rows:
        d = dict(r)
        d["is_shared"] = bool(d["is_shared"])
        d["is_owner"] = bool(d["is_owner"])
        boards.append(d)
    return boards


def create_board(owner_id: int, org_id: int, name: str, color: str = "#5b8cff") -> int:
    name = (name or "").strip() or "Nuevo tablero"
    with get_connection() as conn:
        pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS n FROM boards WHERE owner_id = %s", (owner_id,)
        ).fetchone()["n"]
        cur = conn.execute(
            "INSERT INTO boards (owner_id, org_id, name, color, position, created_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (owner_id, org_id, name, color, pos, _now()),
        )
        return cur.fetchone()["id"]


def update_board(board_id: int, owner_id: int, name: str | None, color: str | None,
                 is_shared: bool | None, member_ids: list[int] | None) -> bool:
    with get_connection() as conn:
        owned = conn.execute(
            "SELECT id FROM boards WHERE id = %s AND owner_id = %s", (board_id, owner_id)
        ).fetchone()
        if not owned:
            return False
        if name is not None:
            conn.execute("UPDATE boards SET name = %s WHERE id = %s", (name.strip(), board_id))
        if color is not None:
            conn.execute("UPDATE boards SET color = %s WHERE id = %s", (color, board_id))
        if is_shared is not None:
            conn.execute("UPDATE boards SET is_shared = %s WHERE id = %s", (1 if is_shared else 0, board_id))
        if member_ids is not None:
            conn.execute("DELETE FROM board_members WHERE board_id = %s", (board_id,))
            for uid in member_ids:
                try:
                    conn.execute("INSERT INTO board_members (board_id, user_id) VALUES (%s,%s)", (board_id, uid))
                except psycopg2.IntegrityError:
                    pass
    return True


def delete_board(board_id: int, owner_id: int) -> bool:
    with get_connection() as conn:
        owned = conn.execute(
            "SELECT id FROM boards WHERE id = %s AND owner_id = %s", (board_id, owner_id)
        ).fetchone()
        if not owned:
            return False
        conn.execute("DELETE FROM tasks WHERE board_id = %s", (board_id,))
        conn.execute("DELETE FROM board_members WHERE board_id = %s", (board_id,))
        conn.execute("DELETE FROM activity_log WHERE board_id = %s", (board_id,))
        conn.execute("DELETE FROM boards WHERE id = %s", (board_id,))
    return True


# ── Settings & admin ────────────────────────────────────────────────────────

def get_setting(org_id: int, key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE org_id = %s AND key = %s", (org_id, key)
        ).fetchone()
    return row["value"] if row else default


def set_setting(org_id: int, key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (org_id, key, value) VALUES (%s, %s, %s) "
            "ON CONFLICT(org_id, key) DO UPDATE SET value = excluded.value",
            (org_id, key, value),
        )



def can_access_board(user_id: int, org_id: int, board_id: int) -> bool:
    with get_connection() as conn:
        return _board_access(conn, board_id, user_id, org_id) is not None


def get_board_members(user_id: int, org_id: int, board_id: int) -> list[int] | None:
    with get_connection() as conn:
        if not _board_access(conn, board_id, user_id, org_id):
            return None
        rows = conn.execute("SELECT user_id FROM board_members WHERE board_id = %s", (board_id,)).fetchall()
    return [r["user_id"] for r in rows]


# ── Activity log ─────────────────────────────────────────────────────────────

def _log(conn, board_id: int, task_id: int | None, user_id: int,
         action: str, detail: str = "") -> None:
    conn.execute(
        "INSERT INTO activity_log (board_id, task_id, user_id, action, detail, created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (board_id, task_id, user_id, action, detail, _now()),
    )


def get_activity(board_id: int, user_id: int, org_id: int, limit: int = 50) -> list[dict] | None:
    with get_connection() as conn:
        if not _board_access(conn, board_id, user_id, org_id):
            return None
        rows = conn.execute(
            """
            SELECT a.action, a.detail, a.created_at, u.username
            FROM activity_log a JOIN users u ON u.id = a.user_id
            WHERE a.board_id = %s ORDER BY a.id DESC LIMIT %s
            """,
            (board_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Tasks ──────────────────────────────────────────────────────────────────────

def get_board_tasks(user_id: int, org_id: int, board_id: int, archived: bool = False) -> dict | None:
    """Grouped active (or archived) tasks for a board the user can access."""
    with get_connection() as conn:
        if not _board_access(conn, board_id, user_id, org_id):
            return None
        rows = conn.execute(
            """
            SELECT t.*, u.username AS assignee_username,
                   (SELECT COUNT(*) FROM subtasks s WHERE s.task_id = t.id) AS subtask_total,
                   (SELECT COUNT(*) FROM subtasks s WHERE s.task_id = t.id AND s.done = 1) AS subtask_done,
                   (SELECT COUNT(*) FROM comments c WHERE c.task_id = t.id) AS comment_count
            FROM tasks t LEFT JOIN users u ON u.id = t.assignee_id
            WHERE t.board_id = %s AND t.archived = %s
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


def _accessible_task(conn, task_id: int, user_id: int, org_id: int):
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if not row or row["board_id"] is None:
        return None
    return row if _board_access(conn, row["board_id"], user_id, org_id) else None


def _next_sort_order(conn, board_id: int, column: str) -> int:
    return conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM tasks "
        "WHERE board_id = %s AND column_name = %s AND archived = 0",
        (board_id, column),
    ).fetchone()["n"]


def create_task(owner_id: int, org_id: int, board_id: int, data: dict) -> int | None:
    column = data.get("column_name", "ToDo")
    tags = ",".join(data.get("tags", []) or [])
    now = _now()
    with get_connection() as conn:
        if not _board_access(conn, board_id, owner_id, org_id):
            return None
        order = _next_sort_order(conn, board_id, column)
        cur = conn.execute(
            """INSERT INTO tasks
               (owner_id, board_id, column_name, text, description, priority, tags, due_date,
                recurrence, assignee_id, sort_order, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (owner_id, board_id, column, data.get("text", ""), data.get("description", ""),
             data.get("priority", "Medium"), tags, data.get("due_date", ""),
             data.get("recurrence", ""), data.get("assignee_id"), order, now, now),
        )
        task_id = cur.fetchone()["id"]
        _log(conn, board_id, task_id, owner_id, "created", data.get("text", ""))
        return task_id


def update_task(task_id: int, user_id: int, org_id: int, data: dict) -> bool:
    """Any board member may edit a task's content."""
    tags = ",".join(data.get("tags", []) or [])
    with get_connection() as conn:
        task = _accessible_task(conn, task_id, user_id, org_id)
        if not task:
            return False
        conn.execute(
            """UPDATE tasks SET text=%s, description=%s, priority=%s, tags=%s, due_date=%s,
               recurrence=%s, column_name=%s, assignee_id=%s, updated_at=%s WHERE id=%s""",
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


def move_task(task_id: int, user_id: int, org_id: int, new_column: str, new_order: int | None = None) -> bool:
    if new_column not in COLUMNS:
        return False
    with get_connection() as conn:
        task = _accessible_task(conn, task_id, user_id, org_id)
        if not task:
            return False
        if new_order is None:
            new_order = _next_sort_order(conn, task["board_id"], new_column)
        conn.execute(
            "UPDATE tasks SET column_name = %s, sort_order = %s, updated_at = %s WHERE id = %s",
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
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (task["owner_id"], task["board_id"], "ToDo", task["text"], task["description"],
                     task["priority"], task["tags"], nxt, task["recurrence"], task["assignee_id"],
                     order, now, now),
                )
                new_task_id = cur.fetchone()["id"]
                _log(conn, task["board_id"], new_task_id, user_id, "created", task["text"])
    return True


def reorder_column(user_id: int, org_id: int, board_id: int, column: str, ordered_ids: list[int]) -> bool:
    if column not in COLUMNS:
        return False
    with get_connection() as conn:
        if not _board_access(conn, board_id, user_id, org_id):
            return False
        for position, tid in enumerate(ordered_ids):
            conn.execute(
                "UPDATE tasks SET column_name = %s, sort_order = %s, updated_at = %s "
                "WHERE id = %s AND board_id = %s",
                (column, position, _now(), tid, board_id),
            )
    return True


def set_archived(task_id: int, user_id: int, org_id: int, archived: bool) -> bool:
    with get_connection() as conn:
        task = _accessible_task(conn, task_id, user_id, org_id)
        if not task:
            return False
        conn.execute(
            "UPDATE tasks SET archived = %s, archived_at = %s, updated_at = %s WHERE id = %s",
            (1 if archived else 0, _now() if archived else "", _now(), task_id),
        )
        _log(conn, task["board_id"], task_id, user_id,
             "archived" if archived else "restored", task["text"])
    return True


def delete_task(task_id: int, user_id: int, org_id: int) -> bool:
    """The task owner or the board owner may delete."""
    with get_connection() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
        if not task or task["board_id"] is None:
            return False
        board = _board_access(conn, task["board_id"], user_id, org_id)
        if not board:
            return False
        if task["owner_id"] != user_id and board["owner_id"] != user_id:
            return False
        conn.execute("DELETE FROM task_shares WHERE task_id = %s", (task_id,))
        conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        _log(conn, task["board_id"], None, user_id, "deleted", task["text"])
    return True


# ── Push subscriptions ─────────────────────────────────────────────────────────

def save_push_subscription(user_id: int, endpoint: str, data_json: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO push_subscriptions (endpoint, user_id, data, created_at) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id, data=excluded.data",
            (endpoint, user_id, data_json, _now()),
        )


def delete_push_subscription(endpoint: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint = %s", (endpoint,))


def get_subscriptions_for_users(user_ids: list[int]) -> list[dict]:
    if not user_ids:
        return []
    placeholders = ",".join(["%s"] * len(user_ids))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT endpoint, data FROM push_subscriptions WHERE user_id IN ({placeholders})",
            user_ids,
        ).fetchall()
    return [dict(r) for r in rows]


# ── Task detail: subtasks, comments, per-task activity ──────────────────────────

def get_task_detail(task_id: int, user_id: int, org_id: int) -> dict | None:
    with get_connection() as conn:
        task = _accessible_task(conn, task_id, user_id, org_id)
        if not task:
            return None
        detail = _task_to_dict(task)
        detail["subtasks"] = [dict(r) | {"done": bool(r["done"])} for r in conn.execute(
            "SELECT id, text, done, position FROM subtasks WHERE task_id = %s ORDER BY position, id",
            (task_id,)).fetchall()]
        detail["comments"] = [dict(r) for r in conn.execute(
            "SELECT c.id, c.body, c.created_at, u.username FROM comments c "
            "JOIN users u ON u.id = c.user_id WHERE c.task_id = %s ORDER BY c.id",
            (task_id,)).fetchall()]
        detail["activity"] = [dict(r) for r in conn.execute(
            "SELECT a.action, a.detail, a.created_at, u.username FROM activity_log a "
            "JOIN users u ON u.id = a.user_id WHERE a.task_id = %s ORDER BY a.id DESC LIMIT 30",
            (task_id,)).fetchall()]
    return detail


def add_subtask(task_id: int, user_id: int, org_id: int, text: str) -> int | None:
    with get_connection() as conn:
        if not _accessible_task(conn, task_id, user_id, org_id):
            return None
        pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS n FROM subtasks WHERE task_id = %s", (task_id,)
        ).fetchone()["n"]
        cur = conn.execute(
            "INSERT INTO subtasks (task_id, text, position, created_at) VALUES (%s,%s,%s,%s) RETURNING id",
            (task_id, text.strip(), pos, _now()),
        )
        return cur.fetchone()["id"]


def update_subtask(subtask_id: int, user_id: int, org_id: int, text: str | None, done: bool | None) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT task_id FROM subtasks WHERE id = %s", (subtask_id,)).fetchone()
        if not row or not _accessible_task(conn, row["task_id"], user_id, org_id):
            return False
        if text is not None:
            conn.execute("UPDATE subtasks SET text = %s WHERE id = %s", (text.strip(), subtask_id))
        if done is not None:
            conn.execute("UPDATE subtasks SET done = %s WHERE id = %s", (1 if done else 0, subtask_id))
    return True


def delete_subtask(subtask_id: int, user_id: int, org_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT task_id FROM subtasks WHERE id = %s", (subtask_id,)).fetchone()
        if not row or not _accessible_task(conn, row["task_id"], user_id, org_id):
            return False
        conn.execute("DELETE FROM subtasks WHERE id = %s", (subtask_id,))
    return True


def add_comment(task_id: int, user_id: int, org_id: int, body: str) -> int | None:
    body = body.strip()
    if not body:
        return None
    with get_connection() as conn:
        if not _accessible_task(conn, task_id, user_id, org_id):
            return None
        cur = conn.execute(
            "INSERT INTO comments (task_id, user_id, body, created_at) VALUES (%s,%s,%s,%s) RETURNING id",
            (task_id, user_id, body, _now()),
        )
        return cur.fetchone()["id"]


def delete_comment(comment_id: int, user_id: int, org_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT c.user_id, t.board_id FROM comments c JOIN tasks t ON t.id = c.task_id "
            "WHERE c.id = %s", (comment_id,)).fetchone()
        if not row:
            return False
        board = _board_access(conn, row["board_id"], user_id, org_id) if row["board_id"] else None
        if not board:
            return False
        if row["user_id"] != user_id and board["owner_id"] != user_id:
            return False
        conn.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
    return True


# ── Due-date reminders ─────────────────────────────────────────────────────────

def due_tasks(date_str: str) -> list[dict]:
    """Unfinished, non-archived tasks due on date_str not yet reminded for it."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, board_id, assignee_id, text FROM tasks
               WHERE due_date = %s AND archived = 0 AND column_name != 'Done'
                 AND COALESCE(reminded_on, '') != %s""",
            (date_str, date_str),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_reminded(task_id: int, date_str: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE tasks SET reminded_on = %s WHERE id = %s", (date_str, task_id))


def board_notify_user_ids(board_id: int, exclude: int | None = None) -> list[int]:
    """Users who should be notified about a board: owner + members (+ the whole
    org if shared — "shared" means shared within the org, never instance-wide)."""
    with get_connection() as conn:
        board = conn.execute(
            "SELECT owner_id, org_id, is_shared FROM boards WHERE id = %s", (board_id,)
        ).fetchone()
        if not board:
            return []
        if board["is_shared"]:
            ids = {r["id"] for r in conn.execute(
                "SELECT id FROM users WHERE org_id = %s AND is_active = TRUE",
                (board["org_id"],),
            ).fetchall()}
        else:
            ids = {board["owner_id"]}
            ids.update(r["user_id"] for r in conn.execute(
                "SELECT user_id FROM board_members WHERE board_id = %s", (board_id,)).fetchall())
            # Drop deactivated members so push/reminders don't target them.
            active = {r["id"] for r in conn.execute(
                "SELECT id FROM users WHERE id = ANY(%s) AND is_active = TRUE",
                (list(ids),),
            ).fetchall()}
            ids = active
    ids.discard(exclude)
    return list(ids)
