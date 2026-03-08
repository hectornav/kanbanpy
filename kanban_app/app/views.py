"""
views.py — Kanbanpy Pro premium board view
Fixes:
  - Tasks not showing: store list widgets + count labels in dicts, no layout traversal
  - Calendar picker for due date
  - Per-user share selection
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QAbstractItemView, QSizePolicy, QDialog, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QFrame, QMenu, QCheckBox, QScrollArea, QCalendarWidget,
    QListWidget as QLW, QDialogButtonBox, QAbstractItemView as AIV
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDate
from app import database as db


COL_META = {
    "ToDo":  {"label": "TODO",  "accent": "#0a84ff"},
    "Doing": {"label": "DOING", "accent": "#ff9f0a"},
    "Done":  {"label": "DONE",  "accent": "#30d158"},
}

# ── Date picker dialog ──────────────────────────────────────────────────────

class DatePickerDialog(QDialog):
    def __init__(self, parent=None, current: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar fecha")
        self.setFixedSize(320, 290)
        layout = QVBoxLayout(self)
        self.cal = QCalendarWidget()
        self.cal.setGridVisible(True)
        self.cal.setStyleSheet("""
            QCalendarWidget { background: white; color: #111; }
            QCalendarWidget QAbstractItemView { color: #111827; background: white;
                selection-background-color: #6366f1; selection-color: white; }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background: #6366f1; }
            QCalendarWidget QToolButton { color: white; background: transparent; font-weight: bold; }
            QCalendarWidget QSpinBox { color: #111; background: white; }
        """)
        if current:
            try:
                d = QDate.fromString(current, "yyyy-MM-dd")
                if d.isValid():
                    self.cal.setSelectedDate(d)
            except Exception:
                pass
        layout.addWidget(self.cal)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def selected_date_str(self) -> str:
        return self.cal.selectedDate().toString("yyyy-MM-dd")


# ── User share picker dialog ─────────────────────────────────────────────────

class UserShareDialog(QDialog):
    def __init__(self, parent=None, owner_id: int = 0, current_ids: list = None):
        super().__init__(parent)
        self.setWindowTitle("Compartir con usuarios")
        self.setMinimumSize(300, 360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Selecciona los usuarios con quienes compartir:"))
        self.lw = QLW()
        self.lw.setSelectionMode(AIV.SelectionMode.MultiSelection)
        self.lw.setStyleSheet("""
            QListWidget { background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 7px; }
            QListWidget::item { padding: 8px 12px; color: #111827; }
            QListWidget::item:selected { background: #e0e7ff; color: #3730a3; }
        """)

        current_ids = current_ids or []
        users = db.get_all_users()
        self._user_rows = []
        for u in users:
            if u['id'] == owner_id:
                continue
            item = QListWidgetItem(f"  👤  {u['username']}")
            item.setData(Qt.ItemDataRole.UserRole, u['id'])
            self.lw.addItem(item)
            self._user_rows.append(item)
            if u['id'] in current_ids:
                item.setSelected(True)

        if self.lw.count() == 0:
            self.lw.addItem(QListWidgetItem("  (No hay otros usuarios registrados)"))

        layout.addWidget(self.lw, 1)

        # Share-with-all checkbox
        self.share_all_cb = QCheckBox("🌐 Compartir con TODOS los usuarios")
        self.share_all_cb.setStyleSheet("color: #374151; font-weight:600;")
        layout.addWidget(self.share_all_cb)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_result(self):
        """Returns (is_shared_globally, [user_ids])"""
        if self.share_all_cb.isChecked():
            return True, []
        ids = [item.data(Qt.ItemDataRole.UserRole)
               for item in self.lw.selectedItems()
               if item.data(Qt.ItemDataRole.UserRole) is not None]
        return False, ids


# ── Task Dialog ──────────────────────────────────────────────────────────────

class TaskDialog(QDialog):
    def __init__(self, parent=None, task_data: dict = None, owner_id: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Editar tarea" if task_data else "Nueva tarea")
        self.setMinimumSize(480, 520)
        self.owner_id = owner_id
        self.task_data = task_data or {
            "text": "", "description": "", "priority": "Medium",
            "tags": [], "due_date": "", "is_shared": False
        }
        self._share_global = bool(self.task_data.get("is_shared", False))
        self._share_ids: list = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(13)
        layout.setContentsMargins(28, 24, 28, 24)

        layout.addWidget(self._lbl("Nombre de la tarea *"))
        self.name_in = QLineEdit(self.task_data["text"])
        self.name_in.setPlaceholderText("¿Qué hay que hacer?")
        layout.addWidget(self.name_in)

        layout.addWidget(self._lbl("Descripción"))
        self.desc_in = QTextEdit(self.task_data["description"])
        self.desc_in.setPlaceholderText("Detalles opcionales…")
        self.desc_in.setMaximumHeight(80)
        layout.addWidget(self.desc_in)

        row = QHBoxLayout()
        # Priority
        c1 = QVBoxLayout()
        c1.addWidget(self._lbl("Prioridad"))
        self.prio_cb = QComboBox()
        self.prio_cb.addItems(["Low", "Medium", "High"])
        self.prio_cb.setCurrentText(self.task_data["priority"])
        c1.addWidget(self.prio_cb)
        row.addLayout(c1)

        # Date picker
        c2 = QVBoxLayout()
        c2.addWidget(self._lbl("Fecha límite"))
        date_row = QHBoxLayout()
        self.date_display = QLineEdit(self.task_data.get("due_date", ""))
        self.date_display.setPlaceholderText("Sin fecha")
        self.date_display.setReadOnly(True)
        self.date_display.setStyleSheet("""
            QLineEdit { background: rgba(120,120,128,0.12); border: 1px solid rgba(84,84,88,0.60);
                        border-radius: 9px; padding: 8px 11px; color: #ffffff; }
        """)
        btn_cal = QPushButton("📅")
        btn_cal.setFixedSize(38, 38)
        btn_cal.setToolTip("Calendario")
        btn_cal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cal.setStyleSheet("""
            QPushButton { background: rgba(120,120,128,0.20); border-radius: 9px; font-size: 16px; border: 1px solid rgba(84,84,88,0.60); }
            QPushButton:hover { background: rgba(120,120,128,0.35); }
        """)
        btn_cal.clicked.connect(self._open_calendar)
        date_row.addWidget(self.date_display, 1)
        date_row.addWidget(btn_cal)
        c2.addLayout(date_row)
        row.addLayout(c2)
        layout.addLayout(row)

        layout.addWidget(self._lbl("Etiquetas (separadas por coma)"))
        self.tags_in = QLineEdit(", ".join(self.task_data["tags"]))
        self.tags_in.setPlaceholderText("urgente, diseño, bug")
        layout.addWidget(self.tags_in)

        # Sharing
        share_row = QHBoxLayout()
        self._share_label = QLabel(self._share_summary())
        self._share_label.setStyleSheet("color:#6366f1; font-weight:600; font-size:12px;")
        share_row.addWidget(self._share_label, 1)
        btn_share = QPushButton("🔗 Compartir…")
        btn_share.setStyleSheet("""
            QPushButton { background:rgba(10,132,255,0.15); color:#0a84ff; border:none;
                          border-radius:7px; padding:7px 14px; font-weight:600; }
            QPushButton:hover { background:rgba(10,132,255,0.25); }
        """)
        btn_share.clicked.connect(self._open_share_dialog)
        share_row.addWidget(btn_share)
        layout.addLayout(share_row)

        layout.addStretch()

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar tarea")
        btn_save.setObjectName("PrimaryButton")
        btn_save.setDefault(True)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.accept)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _open_calendar(self):
        dlg = DatePickerDialog(self, self.date_display.text())
        if dlg.exec():
            self.date_display.setText(dlg.selected_date_str())

    def _open_share_dialog(self):
        dlg = UserShareDialog(self, self.owner_id, self._share_ids)
        if dlg.exec():
            self._share_global, self._share_ids = dlg.get_result()
            self._share_label.setText(self._share_summary())

    def _share_summary(self):
        if self._share_global:
            return "🌐 Compartida con todos"
        if self._share_ids:
            return f"🔗 Compartida con {len(self._share_ids)} usuario(s)"
        return "🔒 Solo tú"

    def get_data(self) -> dict:
        return {
            "text":        self.name_in.text().strip(),
            "description": self.desc_in.toPlainText(),
            "priority":    self.prio_cb.currentText(),
            "tags":        [t.strip() for t in self.tags_in.text().split(",") if t.strip()],
            "due_date":    self.date_display.text().strip(),
            "is_shared":   self._share_global,
        }

    def get_shared_ids(self) -> list:
        return self._share_ids

    def _lbl(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#374151; font-weight:700; font-size:12px;")
        return lbl


# ── Task Card ────────────────────────────────────────────────────────────────

class TaskCard(QFrame):
    def __init__(self, task_data: dict, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.setObjectName("TaskCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 14, 16, 14)

        # Header Row
        hdr = QHBoxLayout()
        hdr.setSpacing(10)

        prio = self.task_data.get("priority", "Medium")
        prio_lbl = QLabel(prio.upper())
        prio_lbl.setObjectName(f"Priority_{prio}")
        prio_lbl.setFixedWidth(58)
        prio_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.addWidget(prio_lbl)

        title_lbl = QLabel(self.task_data.get("text", ""))
        title_lbl.setObjectName("TaskTitle")
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("font-weight: 600; font-size: 14px; color: #ffffff; background: transparent;")
        hdr.addWidget(title_lbl, 1)
        layout.addLayout(hdr)

        # Description
        desc = self.task_data.get("description", "")
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("color: #98989d; font-size: 12px; background: transparent;")
            desc_lbl.setMaximumHeight(36)
            layout.addWidget(desc_lbl)

        # Bottom Row
        footer = QHBoxLayout()
        footer.setSpacing(6)

        tag_box = QWidget()
        tag_box.setStyleSheet("background: transparent;")
        tag_layout = QHBoxLayout(tag_box)
        tag_layout.setContentsMargins(0, 0, 0, 0)
        tag_layout.setSpacing(4)
        for tag in self.task_data.get("tags", [])[:2]:
            t = QLabel(tag)
            t.setObjectName("TagLabel")
            tag_layout.addWidget(t)
        
        footer.addWidget(tag_box)
        footer.addStretch()

        if self.task_data.get("is_shared"):
            s = QLabel("🔗")
            s.setObjectName("SharedBadge")
            s.setToolTip("Compartida")
            footer.addWidget(s)

        date = self.task_data.get("due_date", "")
        if date:
            d = QLabel(f"📅 {date}")
            d.setStyleSheet("color: #98989d; font-size: 11px; font-weight: 500; background: transparent;")
            footer.addWidget(d)

        layout.addLayout(footer)


# ── Kanban List Widget ────────────────────────────────────────────────────────

class KanbanListWidget(QListWidget):
    def __init__(self, column_name: str, kanban_view: "KanbanView", parent=None):
        super().__init__(parent)
        self.column_name = column_name
        self.kanban_view = kanban_view
        self.setObjectName(f"{column_name}List")
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background:transparent; border:none; outline:0;")

    def dropEvent(self, event):
        source: "KanbanListWidget" = event.source()
        if source and source is not self:
            idxs = source.selectedIndexes()
            if idxs:
                event.acceptProposedAction()
                self.kanban_view.move_task_requested.emit(
                    source.column_name, idxs[0].row(), self.column_name
                )
            else:
                event.ignore()
        else:
            event.ignore()


# ── Main Kanban View ──────────────────────────────────────────────────────────

class KanbanView(QWidget):
    add_task_requested    = pyqtSignal(str, object, object)   # col, data (dict), shared_ids (list)
    edit_task_requested   = pyqtSignal(str, int, object, object)
    remove_task_requested = pyqtSignal(str, int)
    move_task_requested   = pyqtSignal(str, int, str)
    logout_requested      = pyqtSignal()

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        # Direct references — no layout traversal needed
        self.list_widgets: dict[str, KanbanListWidget] = {}
        self.count_labels: dict[str, QLabel] = {}
        self._build()

    def _build(self):
        self.setWindowTitle("Kanbanpy Pro")
        self.resize(1140, 780)

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QWidget()
        header.setObjectName("AppHeader")
        header.setFixedHeight(58)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(22, 0, 22, 0)
        hl.setSpacing(14)

        logo = QLabel("📋")
        logo.setStyleSheet("font-size:22px; background:transparent;")
        title = QLabel("Kanbanpy Pro")
        title.setObjectName("HeaderTitle")
        hl.addWidget(logo)
        hl.addWidget(title)
        hl.addStretch()

        user_lbl = QLabel(f"👤 {self.user['username']}")
        user_lbl.setObjectName("HeaderUser")
        hl.addWidget(user_lbl)

        btn_logout = QPushButton("Cerrar sesión")
        btn_logout.setObjectName("LogoutBtn")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.clicked.connect(self.logout_requested.emit)
        hl.addWidget(btn_logout)
        root.addWidget(header)

        # Board
        body = QWidget()
        body.setObjectName("BoardBody")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(18, 18, 18, 14)
        body_layout.setSpacing(16)

        for col_name, meta in COL_META.items():
            col_widget = QWidget()
            col_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: #1c1c1e;
                    border-radius: 14px;
                    border-top: 3px solid {meta['accent']};
                }}
            """)
            col_layout = QVBoxLayout(col_widget)
            col_layout.setContentsMargins(12, 14, 12, 12)
            col_layout.setSpacing(10)

            # Header
            hdr_row = QHBoxLayout()
            col_lbl = QLabel(meta["label"])
            col_lbl.setStyleSheet(f"font-size:11px; font-weight:900; letter-spacing:2px; color:{meta['accent']}; background:transparent;")
            count_lbl = QLabel("0")
            count_lbl.setObjectName("CountBadge")
            count_lbl.setFixedSize(28, 20)
            hdr_row.addWidget(col_lbl)
            hdr_row.addStretch()
            hdr_row.addWidget(count_lbl)
            col_layout.addLayout(hdr_row)
            self.count_labels[col_name] = count_lbl  # direct ref ✓

            # Per-column add button
            btn_add_col = QPushButton(f"＋ Añadir tarea")
            btn_add_col.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {meta['accent']};
                    border: 1px dashed rgba(255,255,255,0.12);
                    border-radius: 8px;
                    padding: 7px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {meta['accent']}18;
                    border: 1px dashed {meta['accent']};
                }}
            """)
            btn_add_col.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_add_col.clicked.connect(
                lambda checked=False, cn=col_name: self._on_add_to_column(cn)
            )
            col_layout.addWidget(btn_add_col)

            # List widget
            lw = KanbanListWidget(col_name, self)
            lw.setSpacing(2)
            lw.itemDoubleClicked.connect(
                lambda item, cn=col_name: self._on_double_click(item, cn)
            )
            lw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lw.customContextMenuRequested.connect(
                lambda pos, cn=col_name: self._on_context_menu(pos, cn)
            )
            col_layout.addWidget(lw, 1)
            self.list_widgets[col_name] = lw  # direct ref ✓

            body_layout.addWidget(col_widget, 1)

        root.addWidget(body, 1)

        # Footer
        footer = QWidget()
        footer.setObjectName("FooterBar")
        footer.setFixedHeight(56)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(22, 0, 22, 0)

        hint = QLabel("Doble clic para editar  ·  Arrastra para mover  ·  Clic derecho para opciones")
        hint.setStyleSheet("color:#475569; font-size:11px; background:transparent;")
        fl.addWidget(hint)
        fl.addStretch()

        btn_add = QPushButton("＋  Nueva tarea")
        btn_add.setObjectName("AddBtn")
        btn_add.setFixedHeight(38)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._on_add_clicked)
        fl.addWidget(btn_add)
        root.addWidget(footer)

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_add_clicked(self):
        self._on_add_to_column("ToDo")

    def _on_add_to_column(self, column: str):
        dlg = TaskDialog(self, owner_id=self.user['id'])
        if dlg.exec():
            data = dlg.get_data()
            if data["text"]:
                self.add_task_requested.emit(column, data, dlg.get_shared_ids())

    def _on_double_click(self, item: QListWidgetItem, column: str):
        lw = self.list_widgets[column]
        row = lw.row(item)
        task_data = item.data(Qt.ItemDataRole.UserRole)
        dlg = TaskDialog(self, task_data, owner_id=self.user['id'])
        if dlg.exec():
            self.edit_task_requested.emit(column, row, dlg.get_data(), dlg.get_shared_ids())

    def _on_context_menu(self, pos, column: str):
        lw: KanbanListWidget = self.sender()
        item = lw.itemAt(pos)
        if not item:
            return
        row = lw.row(item)
        menu = QMenu(self)
        menu.addAction("✏️  Editar").triggered.connect(
            lambda: self._open_edit(item, column, row)
        )
        menu.addAction("🗑️  Eliminar").triggered.connect(
            lambda: self.remove_task_requested.emit(column, row)
        )
        menu.addSeparator()
        cols = list(COL_META.keys())
        for target in cols:
            if target != column:
                arrow = "→" if cols.index(target) > cols.index(column) else "←"
                menu.addAction(f"{arrow}  Mover a {COL_META[target]['label']}").triggered.connect(
                    lambda checked=False, t=target: self.move_task_requested.emit(column, row, t)
                )
        menu.exec(lw.mapToGlobal(pos))

    def _open_edit(self, item, column, row):
        task_data = item.data(Qt.ItemDataRole.UserRole)
        dlg = TaskDialog(self, task_data, owner_id=self.user['id'])
        if dlg.exec():
            self.edit_task_requested.emit(column, row, dlg.get_data(), dlg.get_shared_ids())

    # ── Rendering — uses DIRECT widget references (no layout traversal) ──────

    def update_tasks(self, tasks: dict):
        for col_name in COL_META:
            task_list = tasks.get(col_name, [])

            # Update count badge directly
            self.count_labels[col_name].setText(str(len(task_list)))

            # Repopulate list widget directly
            lw = self.list_widgets[col_name]
            lw.clear()

            for task_data in task_list:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, task_data)
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsSelectable |
                    Qt.ItemFlag.ItemIsDragEnabled
                )
                card = TaskCard(task_data)
                card.setMinimumWidth(lw.width() - 10)
                card.adjustSize()
                sh = card.sizeHint()
                item.setSizeHint(QSize(sh.width(), max(sh.height(), 72) + 8))
                lw.addItem(item)
                lw.setItemWidget(item, card)