from PyQt6.QtCore import QObject, pyqtSignal
import json
import os

class KanbanModel(QObject):
    data_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.tasks = {
            "ToDo": [],
            "Doing": [],
            "Done": []
        }
        self.load_data()

    def add_task(self, column, task_text):
        if task_text.strip():
            self.tasks[column].append({"text": task_text})
            self.save_data()
            self.data_changed.emit()

    def edit_task(self, column, row, new_text):
        if new_text.strip():
            self.tasks[column][row]["text"] = new_text
            self.save_data()
            self.data_changed.emit()

    def remove_task(self, column, row):
        if 0 <= row < len(self.tasks[column]):
            self.tasks[column].pop(row)
            self.save_data()
            self.data_changed.emit()

    
    def move_task(self, from_col, from_row, to_col):
        if (from_col in self.tasks and to_col in self.tasks and
            0 <= from_row < len(self.tasks[from_col])):
            task = self.tasks[from_col].pop(from_row)
            self.tasks[to_col].append(task)
            self.save_data()  # ¡Esta línea es crucial!
            self.data_changed.emit()

    def save_data(self):
        with open("kanban_data.json", "w") as f:
            json.dump(self.tasks, f)

    def load_data(self):
        if os.path.exists("kanban_data.json"):
            with open("kanban_data.json", "r") as f:
                try:
                    self.tasks = json.load(f)
                except json.JSONDecodeError:
                    pass