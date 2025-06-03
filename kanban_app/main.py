import sys
from PyQt6.QtWidgets import QApplication
from app.models import KanbanModel
from app.views import KanbanView
from app.controllers import KanbanController
from app.styles import STYLESHEET

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    
    model = KanbanModel()
    view = KanbanView()
    controller = KanbanController(model, view)
    
    view.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()