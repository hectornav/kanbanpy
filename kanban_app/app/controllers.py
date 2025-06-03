from PyQt6.QtCore import QObject

class KanbanController(QObject):
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view

        # Connect signals
        self.view.add_task_requested.connect(self.add_task)
        self.view.edit_task_requested.connect(self.edit_task)
        self.view.remove_task_requested.connect(self.remove_task)
        self.view.move_task_requested.connect(self.move_task)
        self.model.data_changed.connect(self.update_view)
        
        # Initial update
        self.update_view()

    def add_task(self, column, task_text):
        self.model.add_task(column, task_text)

    def edit_task(self, column, row, new_text):
        self.model.edit_task(column, row, new_text)

    def remove_task(self, column, row):
        self.model.remove_task(column, row)

    def move_task(self, from_col, from_row, to_col):
        self.model.move_task(from_col, from_row, to_col)

    def update_view(self):
        self.view.update_tasks(self.model.tasks)