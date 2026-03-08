"""
models.py - SQLite-backed KanbanModel for Kanbanpy Pro
"""
from PyQt6.QtCore import QObject, pyqtSignal
from app import database as db


class KanbanModel(QObject):
    data_changed = pyqtSignal()

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.user_id = user['id']
        self.tasks = {'ToDo': [], 'Doing': [], 'Done': []}
        self.load_data()

    def load_data(self):
        self.tasks = db.get_tasks_for_user(self.user_id)

    def add_task(self, column: str, task_data: dict, shared_user_ids: list = None):
        if not task_data.get('text', '').strip():
            return
        task_data = dict(task_data)
        task_data['column_name'] = column
        db.add_task(self.user_id, task_data, shared_user_ids or [])
        self.load_data()
        self.data_changed.emit()

    def edit_task(self, column: str, row: int, new_data: dict, shared_user_ids: list = None):
        task_list = self.tasks.get(column, [])
        if 0 <= row < len(task_list):
            task_id = task_list[row]['id']
            new_data = dict(new_data)
            new_data['column_name'] = column
            db.update_task(task_id, new_data, shared_user_ids)
            self.load_data()
            self.data_changed.emit()

    def remove_task(self, column: str, row: int):
        task_list = self.tasks.get(column, [])
        if 0 <= row < len(task_list):
            task_id = task_list[row]['id']
            db.delete_task(task_id)
            self.load_data()
            self.data_changed.emit()

    def move_task(self, from_col: str, from_row: int, to_col: str):
        task_list = self.tasks.get(from_col, [])
        if 0 <= from_row < len(task_list):
            task_id = task_list[from_row]['id']
            db.move_task(task_id, to_col)
            self.load_data()
            self.data_changed.emit()