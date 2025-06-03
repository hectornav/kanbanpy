from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QListWidget, QListWidgetItem, QLineEdit, 
                            QPushButton, QAbstractItemView, QInputDialog,
                            QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QFontMetrics, QColor

class KanbanView(QWidget):
    add_task_requested = pyqtSignal(str, str)  
    edit_task_requested = pyqtSignal(str, int, str)  
    remove_task_requested = pyqtSignal(str, int)  
    move_task_requested = pyqtSignal(str, int, str)  

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Kanban App")
        self.resize(800, 600)

        # Layout principal (vertical)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        # --- Área de columnas ---
        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setContentsMargins(4, 4, 4, 4)
        
        self.columns = {
            "ToDo": self.create_column("ToDo"),
            "Doing": self.create_column("Doing"),
            "Done": self.create_column("Done")
        }

        for column in self.columns.values():
            columns_layout.addLayout(column)

        main_layout.addWidget(columns_container, 1)


        # --- área de entrada en la parte inferior ---
        input_area = QWidget()
        input_layout = QHBoxLayout(input_area)
        input_layout.setContentsMargins(10, 10, 10, 10)

        self.task_input = QLineEdit()
        #ésta linea enviará la tarea al presionar Enter
        self.task_input.returnPressed.connect(self.on_add_clicked)
        self.task_input.setPlaceholderText("New task...")
        self.task_input.setStyleSheet("""
                                        QLineEdit {
                                            font-size: 14px;
                                            padding: 10px;
                                            border: 1px solid #ccc;
                                            border-radius: 8px;
                                        }
                                        QLineEdit:focus {
                                            border-color: #007AFF;
                                        }
                                    """)
        self.task_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        input_layout.addWidget(self.task_input)

        btn_add = QPushButton("+")
        btn_add.setFixedWidth(50)
        btn_add.setStyleSheet("""
                                QPushButton {
                                    font-size: 18px;
                                    font-weight: bold;
                                    background-color: #007AFF;
                                    color: white;
                                    border: none;
                                    border-radius: 8px;
                                }
                                QPushButton:hover {
                                    background-color: #005FCC;
                                }
                            """)
        btn_add.clicked.connect(self.on_add_clicked)
        input_layout.addWidget(btn_add)

        main_layout.addWidget(input_area)

    def create_column(self, title):
        column_layout = QVBoxLayout()
        column_layout.setSpacing(3)

        # Título de columna
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if title == "ToDo":
            lbl_title.setObjectName("ToDo")
        elif title == "Doing":
            lbl_title.setObjectName("Doing")
        elif title == "Done":
            lbl_title.setObjectName("Done")

        column_layout.addWidget(lbl_title)

        # Lista de tareas
        list_widget = KanbanListWidget(title, self)  # Usamos nuestra clase personalizada
        
        list_widget.setStyleSheet("""
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)
        list_widget.setSpacing(3)
        
        # Conexiones de eventos
        list_widget.itemDoubleClicked.connect(
            lambda item, col=title: self.on_item_double_clicked(item, col))
        list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        list_widget.customContextMenuRequested.connect(
            lambda pos, col=title: self.show_context_menu(pos, col))
        
        column_layout.addWidget(list_widget, 1)
        return column_layout

    def on_add_clicked(self):
        task_text = self.task_input.text()
        if task_text.strip():
            self.add_task_requested.emit("ToDo", task_text)
            self.task_input.clear()

    def on_item_double_clicked(self, item, column):
        list_widget = item.listWidget()
        row = list_widget.row(item)
        new_text, ok = QInputDialog.getText(
            self, "Editar tarea", "Nuevo texto:", text=item.text())
        if ok:
            self.edit_task_requested.emit(column, row, new_text)

    def show_context_menu(self, pos, column):
        list_widget = self.sender()
        item = list_widget.itemAt(pos)
        if item:
            row = list_widget.row(item)
            menu = QMenu(self)  
            
            # Añadir opción de eliminar
            remove_action = menu.addAction("❌ Remove task")
            remove_action.triggered.connect(
                lambda: self.remove_task_requested.emit(column, row))
            
            # Añadir opciones de mover
            if column != "ToDo":
                move_action = menu.addAction(f"← Move to 'ToDo'")
                move_action.triggered.connect(
                    lambda: self.move_task_requested.emit(column, row, "ToDo"))
            
            if column != "Doing":
                move_action = menu.addAction(f"→ Move to 'Doing'")
                move_action.triggered.connect(
                    lambda: self.move_task_requested.emit(column, row, "Doing"))
            
            if column != "Done":
                move_action = menu.addAction(f"→ Move to 'Done'")
                move_action.triggered.connect(
                    lambda: self.move_task_requested.emit(column, row, "Done"))
            
            menu.exec(list_widget.mapToGlobal(pos))

    def update_tasks(self, tasks):
        for column_name, column_layout in self.columns.items():
            list_widget = column_layout.itemAt(1).widget()
            list_widget.clear()
            
            for task in tasks[column_name]:
                item = QListWidgetItem(task["text"])
                item.setFlags(item.flags() | 
                            Qt.ItemFlag.ItemIsDragEnabled | 
                            Qt.ItemFlag.ItemIsDropEnabled)
                list_widget.addItem(item)
            
            # Actualizar tamaños después de añadir items
            if list_widget.count() > 0:
                list_widget.update_item_sizes()


class KanbanListWidget(QListWidget):
    def __init__(self, column_name, parent=None):
        super().__init__(parent)
        self.column_name = column_name
        self.setObjectName(f"{column_name}List")  # Para el CSS

        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        
        self.setWordWrap(True)
        self.setUniformItemSizes(False)
        self.setTextElideMode(Qt.TextElideMode.ElideNone)
        
        # Asegurar el cálculo correcto del tamaño
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        source = event.source()
        if source and source != self:
            selected_items = source.selectedItems()
            if selected_items:
                item = selected_items[0]
                parent = self.parent().parent()  # Acceder a KanbanView
                
                # Emitir señal para mover en el modelo
                parent.move_task_requested.emit(
                    source.column_name,
                    source.row(item),
                    self.column_name
                )
                
                # IMPORTANTE: No llamar al dropEvent por defecto
                event.accept()
                return
                
        # Solo permitir el comportamiento por defecto para movimientos internos
        super().dropEvent(event)

    def resizeEvent(self, event):
        """Actualizar tamaños al redimensionar"""
        super().resizeEvent(event)
        self.update_item_sizes()

    def update_item_sizes(self):
        """Ajustar tamaño de todos los items"""
        for i in range(self.count()):
            item = self.item(i)
            if item:
                self.set_item_size(item)

    def set_item_size(self, item):
        """Calcular tamaño óptimo para un item con margen adicional"""
        text = item.text()
        font_metrics = QFontMetrics(self.font())
        
        # Calcular ancho disponible (restamos scrollbar y márgenes)
        available_width = self.viewport().width() - 25
        
        # Calcular el rectángulo de texto necesario
        text_rect = font_metrics.boundingRect(
            QRect(0, 0, available_width, 2000),  # Altura muy grande para contenido largo
            Qt.TextFlag.TextWordWrap | Qt.TextFlag.TextExpandTabs | Qt.TextFlag.TextShowMnemonic,
            text
        )
        
        # Añadir márgenes generosos (padding + border + espacio extra)
        extra_space = 25  # Espacio adicional para asegurar visibilidad completa
        height = text_rect.height() + extra_space
        
        # Establecer tamaño mínimo y máximo razonable
        min_height = 60  # Altura mínima para items cortos
        max_height = 500  # Altura máxima para evitar items gigantes
        final_height = min(max(height, min_height), max_height)
        
        item.setSizeHint(QSize(available_width, final_height))