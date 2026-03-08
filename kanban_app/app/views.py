"""
views.py — Kanbanpy Pro · Final Technical Polish
- Fixing DnD protocol with event acceptance.
- TaskCard uses WA_StyledBackground + explicit inline stylesheet for reliability.
- Date Picker button updated with better SF Pro-style elegance.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QAbstractItemView, QSizePolicy, QDialog, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QFrame, QMenu, QCheckBox, QScrollArea, QCalendarWidget,
    QDialogButtonBox
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
        self.setFixedSize(360, 420)
        self.setStyleSheet("background: #1c1c1e; border-radius: 12px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        self.cal = QCalendarWidget()
        self.cal.setGridVisible(False)
        self.cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.cal.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        
        # Premium Apple Theme for Calendar
        self.cal.setStyleSheet("""
            QCalendarWidget { 
                background: #1c1c1e; 
                color: #ffffff; 
                border: none;
            }
            QCalendarWidget QAbstractItemView { 
                background-color: #1c1c1e; 
                color: #ffffff; 
                selection-background-color: #0a84ff; 
                selection-color: white; 
                outline: none;
                font-size: 13px;
                border-radius: 8px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar { 
                background: #2c2c2e; 
                border-bottom: 1px solid #3a3a3c; 
                min-height: 48px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QCalendarWidget QToolButton { 
                color: #ffffff; 
                background: transparent; 
                font-weight: 800; 
                font-size: 14px;
                icon-size: 24px, 24px;
                padding: 10px;
            }
            QCalendarWidget QToolButton:hover { 
                background-color: rgba(255,255,255,0.1); 
                border-radius: 6px; 
            }
            QCalendarWidget QMenu { 
                background-color: #2c2c2e; 
                color: white; 
                border: 1px solid #3a3a3c; 
            }
            QCalendarWidget QSpinBox {
                color: white; background: #3a3a3c; border: none; font-size: 14px; font-weight: bold;
            }
        """)

        if current:
            try:
                d = QDate.fromString(current, "yyyy-MM-dd")
                if d.isValid():
                    self.cal.setSelectedDate(d)
                else:
                    self.cal.setSelectedDate(QDate.currentDate())
            except Exception:
                self.cal.setSelectedDate(QDate.currentDate())
        else:
            self.cal.setSelectedDate(QDate.currentDate())

        layout.addWidget(self.cal, 1)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("background: transparent; color: #98989d; border: none; font-weight: 600;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Seleccionar")
        btn_ok.setStyleSheet("""
            QPushButton { background: #0a84ff; color: white; border-radius: 10px; padding: 10px 20px; font-weight: bold; }
            QPushButton:hover { background: #007aff; }
        """)
        btn_ok.clicked.connect(self.accept)
        
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        layout.addLayout(btns)

    def selected_date_str(self) -> str:
        return self.cal.selectedDate().toString("yyyy-MM-dd")


# ── User share picker dialog ─────────────────────────────────────────────────

class UserShareDialog(QDialog):
    def __init__(self, parent=None, owner_id: int = 0, current_ids: list = None):
        super().__init__(parent)
        self.setWindowTitle("Compartir tarea")
        self.setMinimumSize(320, 380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        L1 = QLabel("Elegir usuarios:")
        L1.setStyleSheet("font-weight:700; color:#ffffff;")
        layout.addWidget(L1)

        self.lw = QListWidget()
        self.lw.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.lw.setStyleSheet("""
            QListWidget { background: #2c2c2e; border: 1px solid #3a3a3c; border-radius: 10px; padding: 5px; }
            QListWidget::item { padding: 10px; color: #f1f5f9; border-radius: 6px; }
            QListWidget::item:selected { background: #0a84ff; color: white; }
        """)

        current_ids = current_ids or []
        users = db.get_all_users()
        for u in users:
            if u['id'] == owner_id: continue
            item = QListWidgetItem(f"👤  {u['username']}")
            item.setData(Qt.ItemDataRole.UserRole, u['id'])
            self.lw.addItem(item)
            if u['id'] in current_ids:
                item.setSelected(True)

        if self.lw.count() == 0:
            self.lw.addItem(QListWidgetItem("(No hay otros usuarios)"))

        layout.addWidget(self.lw, 1)

        self.share_all_cb = QCheckBox("🌐 Compartir con TODOS")
        self.share_all_cb.setStyleSheet("color:#ff9f0a; font-weight:600;")
        layout.addWidget(self.share_all_cb)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_result(self):
        if self.share_all_cb.isChecked(): return True, []
        ids = [i.data(Qt.ItemDataRole.UserRole) for i in self.lw.selectedItems() if i.data(Qt.ItemDataRole.UserRole)]
        return False, ids


class ClickableLineEdit(QLineEdit):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()

# ── Task Dialog ──────────────────────────────────────────────────────────────

class TaskDialog(QDialog):
    def __init__(self, parent=None, task_data: dict = None, owner_id: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Detalles de la tarea")
        self.setMinimumSize(480, 540)
        self.owner_id = owner_id
        self.task_data = task_data or {
            "text": "", "description": "", "priority": "Medium",
            "tags": [], "due_date": "", "is_shared": False
        }
        self._share_global = bool(self.task_data.get("is_shared", False))
        self._share_ids = []
        if task_data and 'id' in task_data:
            self._share_ids = db.get_shared_user_ids(task_data['id'])
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(32, 28, 32, 28)

        layout.addWidget(self._lbl("NOMBRE DE LA TAREA"))
        self.name_in = QLineEdit(self.task_data["text"])
        self.name_in.setPlaceholderText("¿Qué hay que hacer?")
        layout.addWidget(self.name_in)

        layout.addWidget(self._lbl("DESCRIPCIÓN"))
        self.desc_in = QTextEdit(self.task_data["description"])
        self.desc_in.setPlaceholderText("Detalles adicionales...")
        self.desc_in.setMaximumHeight(90)
        layout.addWidget(self.desc_in)

        row = QHBoxLayout()
        # Priority
        c1 = QVBoxLayout()
        c1.addWidget(self._lbl("PIORIDAD"))
        self.prio_cb = QComboBox()
        self.prio_cb.addItems(["Low", "Medium", "High"])
        self.prio_cb.setCurrentText(self.task_data["priority"])
        c1.addWidget(self.prio_cb)
        row.addLayout(c1)

        # Date
        c2 = QVBoxLayout()
        c2.addWidget(self._lbl("FECHA LÍMITE"))
        self.date_display = ClickableLineEdit(self.task_data.get("due_date", ""))
        self.date_display.setReadOnly(True)
        self.date_display.setPlaceholderText("Seleccionar fecha...")
        self.date_display.setCursor(Qt.CursorShape.PointingHandCursor)
        self.date_display.setStyleSheet("""
            QLineEdit { 
                background: rgba(255,255,255,0.06); 
                color: #ffffff; 
                border: 1px solid rgba(255,255,255,0.1);
                padding: 8px 12px;
                border-radius: 8px;
            }
            QLineEdit:hover { background: rgba(255,255,255,0.1); border-color: #0a84ff; }
        """)
        self.date_display.clicked.connect(self._open_calendar)
        c2.addWidget(self.date_display)
        row.addLayout(c2)
        layout.addLayout(row)

        layout.addWidget(self._lbl("ETIQUETAS"))
        self.tags_in = QLineEdit(", ".join(self.task_data["tags"]))
        self.tags_in.setPlaceholderText("separar por comas...")
        layout.addWidget(self.tags_in)

        layout.addSpacing(10)
        share_box = QWidget()
        share_box.setStyleSheet("background:rgba(10,132,255,0.08); border-radius:12px; border: 1px solid rgba(10,132,255,0.2);")
        sh_lay = QHBoxLayout(share_box)
        sh_lay.setContentsMargins(16, 12, 16, 12)
        
        self.share_lbl = QLabel(self._share_summary())
        self.share_lbl.setStyleSheet("color:#0a84ff; font-weight:700; border:none;")
        sh_lay.addWidget(self.share_lbl, 1)
        
        btn_sh = QPushButton("Configurar…")
        btn_sh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sh.setStyleSheet("QPushButton { font-weight:700; color:#0a84ff; border:none; background:transparent; } QPushButton:hover { color:#3395ff; }")
        btn_sh.clicked.connect(self._open_share_dialog)
        sh_lay.addWidget(btn_sh)
        layout.addWidget(share_box)

        layout.addStretch()

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
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
            self.share_lbl.setText(self._share_summary())

    def _share_summary(self):
        if self._share_global: return "🌐  Público para todos"
        if self._share_ids: return f"🔗  Compartido ({len(self._share_ids)} pers.)"
        return "🔒  Privado (solo tú)"

    def get_data(self) -> dict:
        return {
            "text": self.name_in.text().strip(),
            "description": self.desc_in.toPlainText().strip(),
            "priority": self.prio_cb.currentText(),
            "tags": [t.strip() for t in self.tags_in.text().split(",") if t.strip()],
            "due_date": self.date_display.text().strip(),
            "is_shared": self._share_global,
        }

    def get_shared_ids(self) -> list:
        return self._share_ids

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet("color:#98989d; font-size:10px; font-weight:800; letter-spacing:1px; background:transparent;")
        return l


# ── Task Card ────────────────────────────────────────────────────────────────

class TaskCard(QFrame):
    move_requested = pyqtSignal(str, int, str) # from_col, row_idx, to_col

    def __init__(self, task_data: dict, column_name: str, row_idx: int, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.column_name = column_name
        self.row_idx = row_idx
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setObjectName("TaskCard")
        
        # Color specific to column
        accent = COL_META.get(column_name, {}).get("accent", "#0a84ff")
        
        # Apple Premium Card: Solid elevated background + left accent border
        self.setStyleSheet(f"""
            QFrame#TaskCard {{
                background-color: #2c2c2e;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-left: 4px solid {accent};
                border-radius: 12px;
            }}
            QFrame#TaskCard:hover {{
                background-color: #3a3a3c;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-left: 5px solid {accent};
            }}
        """)
        self._build()

    def _build(self):
        L = QVBoxLayout(self)
        L.setContentsMargins(20, 18, 20, 18)
        L.setSpacing(12)

        # 1. Header (Priority + Move Buttons)
        hdr = QHBoxLayout()
        prio = self.task_data.get("priority", "Medium")
        p_styles = {
            "High":   {"bg": "#ff453a", "text": "#ffffff"},
            "Medium": {"bg": "#ffcc00", "text": "#000000"}, # Black text on yellow for contrast
            "Low":    {"bg": "#30d158", "text": "#ffffff"}
        }
        st = p_styles.get(prio, p_styles["Medium"])
        
        p_lbl = QLabel(prio.upper())
        p_lbl.setStyleSheet(f"""
            color: {st['text']}; font-weight: 900; font-size: 10px; 
            background: {st['bg']}; border-radius: 6px; padding: 4px 10px; 
            border: none;
        """)
        hdr.addWidget(p_lbl)
        hdr.addStretch()

        # Navigation Buttons (← / →)
        cols = list(COL_META.keys())
        idx = cols.index(self.column_name)
        
        if idx > 0:
            hdr.addWidget(self._nav_btn("←", cols[idx-1]))
        if idx < len(cols) - 1:
            hdr.addWidget(self._nav_btn("→", cols[idx+1]))

        L.addLayout(hdr)

        # 2. Title (Bold and clear)
        t_lbl = QLabel(self.task_data.get("text", ""))
        t_lbl.setWordWrap(True)
        t_lbl.setStyleSheet("font-weight: 700; font-size: 16px; color: #ffffff; background: transparent; border: none;")
        L.addWidget(t_lbl)

        # 3. Description
        desc = self.task_data.get("description", "")
        if desc:
            d_lbl = QLabel(desc)
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color: #98989d; font-size: 13px; background: transparent; border: none;")
            d_lbl.setMaximumHeight(45)
            L.addWidget(d_lbl)

        # 4. Footer (Tags + Date)
        footer = QHBoxLayout()
        for tag in self.task_data.get("tags", [])[:2]:
            t = QLabel(tag)
            t.setStyleSheet("color: #ffffff; background: rgba(120, 120, 128, 0.4); border-radius: 6px; padding: 3px 9px; font-size: 11px; font-weight: 700; border: none;")
            footer.addWidget(t)
        
        footer.addStretch()
        
        date = self.task_data.get("due_date", "")
        if date:
            dt_lbl = QLabel(f"📅 {date}")
            dt_lbl.setStyleSheet("color: #98989d; font-size: 11px; font-weight: 700; background: transparent; border: none;")
            footer.addWidget(dt_lbl)
        L.addLayout(footer)

    def _nav_btn(self, text, target):
        btn = QPushButton(text)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(f"Mover a {target}")
        btn.setStyleSheet("""
            QPushButton { 
                background: rgba(120, 120, 128, 0.25); 
                color: #ffffff; 
                border: none; 
                border-radius: 14px; 
                font-size: 15px; 
                font-weight: 900;
            }
            QPushButton:hover { 
                background: rgba(120, 120, 128, 0.45); 
                color: #ffffff;
            }
        """)
        btn.clicked.connect(lambda: self.move_requested.emit(self.column_name, self.row_idx, target))
        return btn


# ── Kanban List Widget ────────────────────────────────────────────────────────

class KanbanListWidget(QListWidget):
    def __init__(self, column_name: str, kanban_view: "KanbanView", parent=None):
        super().__init__(parent)
        self.column_name = column_name
        self.kanban_view = kanban_view
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setStyleSheet("QListWidget { background:transparent; border:none; outline:none; }")

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            e.acceptProposedAction()
        else: super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            e.acceptProposedAction()
        else: super().dragMoveEvent(e)

    def dropEvent(self, e):
        source = e.source()
        if source and source != self:
            item = source.currentItem()
            if item:
                row = source.row(item)
                # Emit signal to model
                self.kanban_view.move_task_requested.emit(source.column_name, row, self.column_name)
                e.acceptProposedAction()
                return
        e.ignore()


# ── Main Kanban View ──────────────────────────────────────────────────────────

class KanbanView(QWidget):
    add_task_requested    = pyqtSignal(str, object, object)
    edit_task_requested   = pyqtSignal(str, int, object, object)
    remove_task_requested = pyqtSignal(str, int)
    move_task_requested   = pyqtSignal(str, int, str)
    logout_requested      = pyqtSignal()

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.lw_map = {}
        self.count_map = {}
        self._build()

    def _build(self):
        self.setWindowTitle("Kanbanpy Pro")
        self.resize(1180, 820)

        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(64)
        hdr.setObjectName("AppHeader")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(28, 0, 28, 0)
        
        logo = QLabel("📋")
        logo.setFixedSize(32, 32)
        logo.setStyleSheet("font-size:24px; background:transparent;")
        title = QLabel("Kanbanpy Pro")
        title.setObjectName("HeaderTitle")
        hl.addWidget(logo)
        hl.addWidget(title)
        hl.addSpacing(20)
        hl.addStretch()

        u_lbl = QLabel(f"👤  {self.user['username']}")
        u_lbl.setObjectName("HeaderUser")
        hl.addWidget(u_lbl)
        hl.addSpacing(16)

        btn_out = QPushButton("Cerrar sesión")
        btn_out.setObjectName("LogoutBtn")
        btn_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_out.clicked.connect(self.logout_requested.emit)
        hl.addWidget(btn_out)
        main_v.addWidget(hdr)

        # Board
        board = QWidget()
        board.setObjectName("BoardBody")
        bl = QHBoxLayout(board)
        bl.setContentsMargins(20, 20, 20, 20)
        bl.setSpacing(20)

        for col, meta in COL_META.items():
            panel = QWidget()
            panel.setStyleSheet(f"background:#1c1c1e; border-radius:18px; border-top: 4px solid {meta['accent']};")
            pl = QVBoxLayout(panel)
            pl.setContentsMargins(14, 18, 14, 14)
            pl.setSpacing(12)

            ph = QHBoxLayout()
            c_label = QLabel(meta["label"])
            c_label.setStyleSheet(f"color:{meta['accent']}; font-weight:900; font-size:11px; letter-spacing:1.5px; background:transparent; border:none;")
            count = QLabel("0")
            count.setObjectName("CountBadge")
            ph.addWidget(c_label)
            ph.addStretch()
            ph.addWidget(count)
            pl.addLayout(ph)
            self.count_map[col] = count

            btn_add = QPushButton("＋  Adicionar tarea")
            btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_add.setStyleSheet(f"QPushButton {{ background:transparent; color:{meta['accent']}; border:1px dashed {meta['accent']}40; border-radius:10px; padding:8px; font-weight:700; }} QPushButton:hover {{ background:{meta['accent']}15; border:1px dashed {meta['accent']}; }}")
            btn_add.clicked.connect(lambda checked, c=col: self._on_add(c))
            pl.addWidget(btn_add)

            lw = KanbanListWidget(col, self)
            lw.itemDoubleClicked.connect(lambda i, c=col: self._on_double(i, c))
            lw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lw.customContextMenuRequested.connect(lambda p, c=col: self._on_menu(p, c))
            pl.addWidget(lw, 1)
            self.lw_map[col] = lw

            bl.addWidget(panel, 1)
        
        main_v.addWidget(board, 1)

        # Footer
        footer = QWidget()
        footer.setObjectName("FooterBar")
        footer.setFixedHeight(60)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(28, 0, 28, 0)
        
        hint = QLabel("💡 Arrastra tareas para moverlas · Doble clic para editar · Clic derecho para opciones")
        hint.setStyleSheet("color:#98989d; font-size:11px; background:transparent;")
        fl.addWidget(hint)
        fl.addStretch()
        
        btn_new = QPushButton("＋  Nueva tarea")
        btn_new.setObjectName("AddBtn")
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.clicked.connect(lambda: self._on_add("ToDo"))
        fl.addWidget(btn_new)
        main_v.addWidget(footer)

    def _on_add(self, col):
        dlg = TaskDialog(self, owner_id=self.user['id'])
        if dlg.exec():
            self.add_task_requested.emit(col, dlg.get_data(), dlg.get_shared_ids())

    def _on_double(self, item, col):
        lw = self.lw_map[col]
        row = lw.row(item)
        task = item.data(Qt.ItemDataRole.UserRole)
        dlg = TaskDialog(self, task, owner_id=self.user['id'])
        if dlg.exec():
            self.edit_task_requested.emit(col, row, dlg.get_data(), dlg.get_shared_ids())

    def _on_menu(self, pos, col):
        lw = self.lw_map[col]
        item = lw.itemAt(pos)
        if not item: return
        row = lw.row(item)
        menu = QMenu(self)
        menu.addAction("✏️  Editar").triggered.connect(lambda: self._on_double(item, col))
        menu.addAction("🗑️  Eliminar").triggered.connect(lambda: self.remove_task_requested.emit(col, row))
        menu.addSeparator()
        for t in COL_META:
            if t != col:
                menu.addAction(f"→  Mover a {COL_META[t]['label']}").triggered.connect(lambda chk, tc=t: self.move_task_requested.emit(col, row, tc))
        menu.exec(lw.mapToGlobal(pos))

    def update_tasks(self, tasks):
        for col, lw in self.lw_map.items():
            data_list = tasks.get(col, [])
            if col in self.count_map:
                self.count_map[col].setText(str(len(data_list)))
            
            lw.clear()
            for i, d in enumerate(data_list):
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, d)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
                
                card = TaskCard(d, col, i)
                card.move_requested.connect(self.move_task_requested.emit)
                
                card.setFixedWidth(lw.width() - 8)
                sh = card.sizeHint()
                item.setSizeHint(QSize(sh.width(), sh.height() + 8))
                lw.addItem(item)
                lw.setItemWidget(item, card)