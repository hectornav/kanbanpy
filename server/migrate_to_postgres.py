#!/usr/bin/env python3
"""One-off data migration: copy an existing Kanbanpy SQLite database into
the Postgres database the app now uses.

Meant to be run manually, once, during cutover — with the app container
stopped so the source SQLite file isn't being written to concurrently.

Usage:
    python migrate_to_postgres.py [path/to/kanban.db]

    - Source path defaults to /data/kanban.db (the Docker/NAS layout).
    - Target is read from the DATABASE_URL environment variable, exactly
      like app/db.py.

The source SQLite file is opened read-only and is never modified or deleted.
Every insert uses `ON CONFLICT ... DO NOTHING`, so the script is safe to
re-run (e.g. if it's interrupted partway through, or you want to re-sync
after fixing something).
"""
import os
import sys
import sqlite3

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values

DEFAULT_SQLITE_PATH = '/data/kanban.db'

# (table, columns, conflict_target, has_serial_id)
# Order matters: FK-dependent tables must come after the tables they
# reference (boards -> users; board_members -> boards/users;
# tasks -> users/boards; task_shares/subtasks/comments -> tasks;
# activity_log -> boards; push_subscriptions -> users).
TABLES = [
    ('users', ['id', 'username', 'password_hash', 'security_q', 'security_a', 'created_at'], ['id'], True),
    ('boards', ['id', 'owner_id', 'name', 'color', 'is_shared', 'position', 'created_at'], ['id'], True),
    ('board_members', ['board_id', 'user_id'], ['board_id', 'user_id'], False),
    ('tasks', [
        'id', 'owner_id', 'board_id', 'column_name', 'text', 'description', 'priority', 'tags',
        'due_date', 'recurrence', 'is_shared', 'assignee_id', 'sort_order', 'archived',
        'archived_at', 'reminded_on', 'created_at', 'updated_at',
    ], ['id'], True),
    ('task_shares', ['task_id', 'user_id'], ['task_id', 'user_id'], False),
    ('activity_log', ['id', 'board_id', 'task_id', 'user_id', 'action', 'detail', 'created_at'], ['id'], True),
    ('subtasks', ['id', 'task_id', 'text', 'done', 'position', 'created_at'], ['id'], True),
    ('comments', ['id', 'task_id', 'user_id', 'body', 'created_at'], ['id'], True),
    ('push_subscriptions', ['endpoint', 'user_id', 'data', 'created_at'], ['endpoint'], False),
    ('settings', ['key', 'value'], ['key'], False),
]


def open_sqlite_readonly(path):
    if not os.path.exists(path):
        print(f'✗ SQLite source database not found: {path}')
        sys.exit(1)
    # uri=True + mode=ro guarantees this connection can never write to the
    # source file, no matter what the rest of the script does.
    uri = f'file:{os.path.abspath(path)}?mode=ro'
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def open_postgres():
    try:
        database_url = os.environ['DATABASE_URL']
    except KeyError:
        print('✗ DATABASE_URL environment variable is not set.')
        sys.exit(1)
    conn = psycopg2.connect(database_url, options='-c timezone=UTC')
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


def table_exists_sqlite(sqlite_conn, table):
    row = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def copy_table(sqlite_conn, pg_conn, table, columns, conflict_target):
    """Copy all rows of one table from SQLite to Postgres. Returns (source_count, dest_total)."""
    if not table_exists_sqlite(sqlite_conn, table):
        print(f'  {table}: source table not found — skipping')
        return 0, None

    col_list_sql = ', '.join(columns)
    rows = sqlite_conn.execute(f'SELECT {col_list_sql} FROM {table}').fetchall()
    source_count = len(rows)

    if source_count > 0:
        values = [tuple(row[c] for c in columns) for row in rows]
        pg_cur = pg_conn.cursor()
        conflict_sql = f"ON CONFLICT ({', '.join(conflict_target)}) DO NOTHING"
        sql = f'INSERT INTO {table} ({col_list_sql}) VALUES %s {conflict_sql}'
        execute_values(pg_cur, sql, values, page_size=500)
        pg_conn.commit()

    dest_total = pg_conn.cursor()
    dest_total.execute(f'SELECT COUNT(*) AS count FROM {table}')
    dest_count = dest_total.fetchone()['count']

    print(f'  {table}: {source_count} rows in source -> {dest_count} rows now in Postgres')
    return source_count, dest_count


def fix_sequence(pg_conn, table):
    """Bump the table's id SEQUENCE past the highest migrated id, so the
    next auto-generated insert doesn't collide with a row we just copied.
    """
    cur = pg_conn.cursor()
    cur.execute(
        "SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE((SELECT MAX(id) FROM " + table + "), 1))",
        (table,)
    )
    pg_conn.commit()


def main():
    sqlite_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SQLITE_PATH

    print(f'Source (SQLite, read-only): {sqlite_path}')
    sqlite_conn = open_sqlite_readonly(sqlite_path)

    pg_conn = open_postgres()
    print('Target (Postgres): connected via DATABASE_URL')
    print()

    print('Copying tables...')
    totals = {}
    for table, columns, conflict_target, has_serial_id in TABLES:
        source_count, dest_count = copy_table(sqlite_conn, pg_conn, table, columns, conflict_target)
        totals[table] = source_count
        if has_serial_id:
            fix_sequence(pg_conn, table)

    sqlite_conn.close()
    pg_conn.close()

    print()
    print('Summary — rows read from SQLite source:')
    for table, columns, conflict_target, has_serial_id in TABLES:
        print(f'  {table:<20} {totals.get(table, 0)}')
    print()
    print('Done. Source SQLite file was not modified.')


if __name__ == '__main__':
    main()
