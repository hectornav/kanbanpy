"""
controllers.py - Wires model ↔ view for Kanbanpy Pro
Updated to handle (col, data, shared_ids) signals.
"""
from PyQt6.QtCore import QObject


class KanbanController(QObject):
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view

        self.view.add_task_requested.connect(self.add_task)
        self.view.edit_task_requested.connect(self.edit_task)
        self.view.remove_task_requested.connect(self.remove_task)
        self.view.move_task_requested.connect(self.move_task)
        self.model.data_changed.connect(self.update_view)

        self.update_view()

    def add_task(self, column: str, task_data: dict, shared_ids: list):
        self.model.add_task(column, task_data, shared_ids)

    def edit_task(self, column: str, row: int, new_data: dict, shared_ids: list):
        self.model.edit_task(column, row, new_data, shared_ids)

    def remove_task(self, column: str, row: int):
        self.model.remove_task(column, row)

    def move_task(self, from_col: str, from_row: int, to_col: str):
        self.model.move_task(from_col, from_row, to_col)

    def update_view(self):
        self.view.update_tasks(self.model.tasks)