"""
reminders.py - Due-date reminder sweeps.

Finds tasks due on a given date that are still open and notifies the assignee
(or the whole board if unassigned) via Web Push, once per due date.
"""
from . import db, push


def run_due_reminders(date_str: str) -> int:
    """Send a reminder for each task due on date_str. Returns how many were processed."""
    tasks = db.due_tasks(date_str)
    for task in tasks:
        if task["assignee_id"]:
            recipients = [task["assignee_id"]]
        else:
            recipients = db.board_notify_user_ids(task["board_id"])
        recipients = [r for r in recipients if r]
        if recipients:
            push.notify_users(recipients, {
                "title": "Vence hoy",
                "body": task["text"],
                "url": "/",
            })
        db.mark_reminded(task["id"], date_str)
    return len(tasks)
