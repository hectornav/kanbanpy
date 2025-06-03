STYLESHEET = """

/* Estilos generales */
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    background: qlineargradient(
        x1: 0, y1: 0,
        x2: 1, y2: 1,
        stop: 0 #2E8B8B,
        stop: 1 #1E3C4D
    );
}
/* Estilos para las listas de cada columna */
#ToDoList {
    background-color: #ffccd5;  /* rosa manzana */
    border-radius: 12px;
    padding: 8px;
}

#DoingList {
    background-color: #ffe680;  /* amarillo suave tipo notas */
    border-radius: 12px;
    padding: 8px;
}

#DoneList {
    background-color: #c8f7c5;  /* verde suave como Mensajes */
    border-radius: 12px;
    padding: 8px;
}

/* Mantén el resto de tus estilos actuales */
QListWidget::item:hover {
    background-color: #e0e0e0;
}
/* Campo de entrada */
QLineEdit {
    padding: 8px 12px;
    border: 1px solid #d2d6db;
    border-radius: 6px;
    background-color: white;
    color: #2c3e50;
    font-size: 14px;
    margin: 8px 0;
}

QLineEdit:focus {
    border-color: #007aff;
    outline: none;
}


/* Botón + */
QPushButton {
    background-color: #007aff;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 30px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #0066d6;
}

/* Títulos de columnas */
QLabel#ToDo {
    background-color: #ff453a;
    color: white;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 14px;
}

QLabel#Doing{
    background-color: #ff9f0a;
    color: white;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 14px;
}

QLabel#Done {
    background-color: #30d158;
    color: white;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 14px;
}

/* Listas de tareas */
QListWidget {
    background-color: #ecf0f1;
    border-radius: 5px;
    padding: 5px;
}

QListWidget::item {
    background-color: white;
    color: #2c3e50;
    border: 1px solid #bdc3c7;
    border-radius: 3px;
    padding: 8px;
    margin: 2px;
}

QListWidget::item:hover {
    background-color: #f8f9fa;
    border-color: #d8dde3;
    
}

QListWidget::item:selected {
    background-color: #f0f5ff;
    border-color: #007aff;
    color: #1c1c1e;
}

QListWidget::item:hover:selected {
    background-color: #e6f0ff;
}

/* Efecto al arrastrar */
QListWidget::item[dragging="true"] {
    background-color: #f0f5ff;
    border: 1px dashed #007aff;
    opacity: 0.8;
}

/* Espaciado entre items */
QListWidget {
    show-decoration-selected: 1;
}

/* Scrollbar */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
}

QScrollBar::handle:vertical {
    background: #c4c9d1;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
"""