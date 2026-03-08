"""
database.py - SQLite persistence layer for Kanbanpy Pro
"""
import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'kanban.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username       TEXT    NOT NULL UNIQUE,
                password_hash  TEXT    NOT NULL,
                security_q     TEXT    DEFAULT '',
                security_a     TEXT    DEFAULT ''
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
                FOREIGN KEY(owner_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS task_shares (
                task_id  INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                PRIMARY KEY (task_id, user_id),
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """)
        # Migrations: add missing columns safely
        user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if 'security_q' not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN security_q TEXT DEFAULT ''")
        if 'security_a' not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN security_a TEXT DEFAULT ''")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ── Users ─────────────────────────────────────────────────────────────────────

def register_user(username: str, password: str, security_q: str = "", security_a: str = ""):
    if not username.strip() or not password.strip():
        return False, "El usuario y la contraseña no pueden estar vacíos."
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, security_q, security_a) VALUES (?,?,?,?)",
                (username.strip(), _hash(password), security_q.strip(), security_a.strip().lower())
            )
        return True, "Usuario registrado."
    except sqlite3.IntegrityError:
        return False, "Ese nombre de usuario ya existe."


def authenticate_user(username: str, password: str):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username.strip(), _hash(password))
        ).fetchone()


def get_security_question(username: str):
    with get_connection() as conn:
        row = conn.execute("SELECT security_q FROM users WHERE username=?", (username.strip(),)).fetchone()
    return row["security_q"] if row else None


def reset_password(username: str, answer: str, new_password: str):
    with get_connection() as conn:
        row = conn.execute("SELECT id, security_a FROM users WHERE username=?", (username.strip(),)).fetchone()
    if not row:
        return False, "Usuario no encontrado."
    if not row["security_a"]:
        return False, "Este usuario no tiene pregunta de seguridad registrada."
    if row["security_a"] != answer.strip().lower():
        return False, "La respuesta no es correcta."
    with get_connection() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE username=?", (_hash(new_password), username.strip()))
    return True, "Contraseña restablecida."


def get_all_users():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT id, username FROM users ORDER BY username").fetchall()]


# ── Tasks ─────────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    d = dict(row)
    d['tags'] = [t for t in d.get('tags', '').split(',') if t]
    d['is_shared'] = bool(d.get('is_shared', 0))
    return d


def get_tasks_for_user(user_id: int) -> dict:
    """Return owned tasks + globally shared + explicitly shared with this user."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT t.* FROM tasks t
            LEFT JOIN task_shares ts ON ts.task_id = t.id
            WHERE t.owner_id = ?
               OR t.is_shared = 1
               OR ts.user_id = ?
            ORDER BY t.id ASC
            """,
            (user_id, user_id)
        ).fetchall()
        
        result = {'ToDo': [], 'Doing': [], 'Done': []}
        for row in rows:
            d = _row_to_dict(row)
            col = d['column_name']
            if col in result:
                result[col].append(d)
        return result
    finally:
        conn.close()


def add_task(owner_id: int, task_data: dict, shared_user_ids: list = None) -> int:
    tags_str = ','.join(task_data.get('tags', []))
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO tasks
               (owner_id, column_name, text, description, priority, tags, due_date, is_shared)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                owner_id,
                task_data.get('column_name', 'ToDo'),
                task_data.get('text', ''),
                task_data.get('description', ''),
                task_data.get('priority', 'Medium'),
                tags_str,
                task_data.get('due_date', ''),
                1 if task_data.get('is_shared') else 0
            )
        )
        task_id = cur.lastrowid
        if shared_user_ids:
            for uid in shared_user_ids:
                try:
                    conn.execute("INSERT INTO task_shares (task_id, user_id) VALUES (?,?)", (task_id, uid))
                except Exception:
                    pass
        conn.commit()
        return task_id
    finally:
        conn.close()


def update_task(task_id: int, task_data: dict, shared_user_ids: list = None):
    tags_str = ','.join(task_data.get('tags', []))
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE tasks SET text=?, description=?, priority=?, tags=?,
               due_date=?, is_shared=?, column_name=? WHERE id=?""",
            (
                task_data.get('text', ''),
                task_data.get('description', ''),
                task_data.get('priority', 'Medium'),
                tags_str,
                task_data.get('due_date', ''),
                1 if task_data.get('is_shared') else 0,
                task_data.get('column_name', 'ToDo'),
                task_id
            )
        )
        if shared_user_ids is not None:
            conn.execute("DELETE FROM task_shares WHERE task_id=?", (task_id,))
            for uid in shared_user_ids:
                try:
                    conn.execute("INSERT INTO task_shares (task_id, user_id) VALUES (?,?)", (task_id, uid))
                except Exception:
                    pass
        conn.commit()
    finally:
        conn.close()


def get_shared_user_ids(task_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT user_id FROM task_shares WHERE task_id=?", (task_id,)).fetchall()
        return [r['user_id'] for r in rows]
    finally:
        conn.close()


def move_task(task_id: int, new_column: str):
    conn = get_connection()
    try:
        conn.execute("UPDATE tasks SET column_name=? WHERE id=?", (new_column, task_id))
        conn.commit()
    finally:
        conn.close()


def delete_task(task_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM task_shares WHERE task_id=?", (task_id,))
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
    finally:
        conn.close()
