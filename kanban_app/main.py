"""
main.py - Entry point for Kanbanpy Pro
Shows login first, then launches the Kanban board.
"""
import sys
from PyQt6.QtWidgets import QApplication
from app import database as db
from app.styles import STYLESHEET
from app.auth_views import AuthWindow
from app.views import KanbanView
from app.models import KanbanModel
from app.controllers import KanbanController


def launch_board(user_data: dict, app: QApplication, auth_window: AuthWindow):
    """Create and show the Kanban board for the given user."""
    auth_window.hide()

    # Store references on auth_window to prevent garbage collection
    auth_window.model = KanbanModel(user_data)
    auth_window.view = KanbanView(user_data)
    auth_window.controller = KanbanController(auth_window.model, auth_window.view)

    def on_logout():
        auth_window.view.close()
        auth_window.login_user.clear()
        auth_window.login_pass.clear()
        auth_window.login_error.setText("")
        auth_window.stack.setCurrentIndex(0)
        auth_window.show()

    auth_window.view.logout_requested.connect(on_logout)
    auth_window.view.show()


def main():
    db.init_db()

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    auth_window = AuthWindow()
    auth_window.login_successful.connect(
        lambda user: launch_board(user, app, auth_window)
    )
    auth_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()