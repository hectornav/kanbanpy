"""
backend.py - Data-source selector for the PyQt6 desktop client.

If KANBAN_API_URL is set, the app talks to the shared Kanbanpy Pro backend on
the NAS (hybrid "Option C" mode). Otherwise it falls back to the legacy local
SQLite database, so the desktop app still runs fully standalone.

The rest of the UI imports this module as `db`, unaware of which one is active.
"""
import os

if os.getenv("KANBAN_API_URL"):
    from . import remote_db as _impl
    MODE = "remote"
else:
    from . import database as _impl
    MODE = "local"

# Re-export the shared data-layer interface.
init_db = _impl.init_db
authenticate_user = _impl.authenticate_user
register_user = _impl.register_user
get_security_question = _impl.get_security_question
reset_password = _impl.reset_password
get_all_users = _impl.get_all_users
get_tasks_for_user = _impl.get_tasks_for_user
add_task = _impl.add_task
update_task = _impl.update_task
move_task = _impl.move_task
delete_task = _impl.delete_task
get_shared_user_ids = _impl.get_shared_user_ids
