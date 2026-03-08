"""
auth_views.py — Kanbanpy Pro · Apple macOS dark mode login/register/forgot
Two-column layout:
  Left  → black brand panel (#000000 bg)
  Right → dark card (#1c1c1e bg)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QStackedWidget, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from app import database as db


class AuthWindow(QWidget):
    login_successful = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setObjectName("AuthWindow")
        self.setWindowTitle("Kanbanpy Pro")
        self.setMinimumSize(800, 560)
        self.resize(860, 580)
        self._build()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left brand panel ──
        left = QFrame()
        left.setObjectName("BrandPanel")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(44, 52, 36, 44)
        lv.setSpacing(10)

        icon = QLabel("📋")
        icon.setStyleSheet("font-size:56px; background:transparent;")
        lv.addWidget(icon)
        lv.addSpacing(8)

        tag = QLabel("Kanbanpy Pro")
        tag.setObjectName("AppTagline")
        lv.addWidget(tag)

        sub = QLabel("Tu forma de trabajar,\norganizada.")
        sub.setObjectName("AppSubTagline")
        sub.setWordWrap(True)
        lv.addWidget(sub)
        lv.addSpacing(40)

        for feat in [
            "✦  Tablero Kanban multi-usuario",
            "✦  Prioridades, etiquetas y fechas",
            "✦  Comparte tareas con tu equipo",
            "✦  Persistencia local con SQLite",
        ]:
            fl = QLabel(feat)
            fl.setStyleSheet("color:rgba(255,255,255,0.45); font-size:12px; background:transparent;")
            lv.addWidget(fl)

        lv.addStretch()
        root.addWidget(left, 3)

        # ── Right form card ──
        right = QFrame()
        right.setObjectName("AuthCard")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(52, 0, 52, 0)
        rv.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:transparent;")
        self.page_login    = self._make_login()
        self.page_register = self._make_register()
        self.page_forgot   = self._make_forgot()
        self.stack.addWidget(self.page_login)     # 0
        self.stack.addWidget(self.page_register)  # 1
        self.stack.addWidget(self.page_forgot)    # 2

        rv.addWidget(self.stack, 1)
        root.addWidget(right, 4)

    # ── Login ────────────────────────────────────────────────────────────────

    def _make_login(self):
        w = self._clear_widget()
        L = QVBoxLayout(w)
        L.setContentsMargins(0, 0, 0, 0)
        L.setSpacing(0)
        L.addStretch()

        L.addWidget(self._h1("Bienvenido/a"))
        L.addSpacing(6)
        L.addWidget(self._sub("Inicia sesión para continuar"))
        L.addSpacing(32)

        L.addWidget(self._field_label("Usuario"))
        L.addSpacing(5)
        self.login_user = self._input("Nombre de usuario")
        L.addWidget(self.login_user)
        L.addSpacing(16)

        L.addWidget(self._field_label("Contraseña"))
        L.addSpacing(5)
        self.login_pass = self._input("Contraseña", pwd=True)
        self.login_pass.returnPressed.connect(self._do_login)
        L.addWidget(self.login_pass)
        L.addSpacing(8)

        # Remember me + Forgot password row
        tools_row = QHBoxLayout()
        self.remember_cb = QCheckBox("Recordar credenciales")
        self.remember_cb.setObjectName("FieldLabel")
        tools_row.addWidget(self.remember_cb)
        tools_row.addStretch()
        btn_forgot = QPushButton("¿Olvidaste tu contraseña?")
        btn_forgot.setObjectName("LinkButton")
        btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_forgot.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        tools_row.addWidget(btn_forgot)
        L.addLayout(tools_row)
        L.addSpacing(12)

        self.login_error = self._err()
        L.addWidget(self.login_error)
        L.addSpacing(24)

        btn = QPushButton("Iniciar sesión")
        btn.setObjectName("AuthPrimary")
        btn.setFixedHeight(46)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._do_login)
        self.login_user.returnPressed.connect(self._do_login)
        self.login_pass.returnPressed.connect(self._do_login)
        L.addWidget(btn)
        L.addSpacing(18)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._sub("¿No tienes cuenta?  "))
        btn2 = QPushButton("Regístrate")
        btn2.setObjectName("LinkButton")
        btn2.setCursor(Qt.CursorShape.PointingHandCursor)
        btn2.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        row.addWidget(btn2)
        row.addStretch()
        L.addLayout(row)
        L.addStretch()

        # Load saved credentials
        settings = QSettings("Kanbanpy", "Pro")
        saved_u = settings.value("login/username", "")
        saved_p = settings.value("login/password", "")
        if saved_u and saved_p:
            self.login_user.setText(saved_u)
            self.login_pass.setText(saved_p)
            self.remember_cb.setChecked(True)

        return w

    def _do_login(self):
        u = self.login_user.text().strip()
        p = self.login_pass.text()
        user = db.authenticate_user(u, p)
        if user:
            self.login_error.setText("")
            
            # Save or clear credentials
            settings = QSettings("Kanbanpy", "Pro")
            if self.remember_cb.isChecked():
                settings.setValue("login/username", u)
                settings.setValue("login/password", p)
            else:
                settings.remove("login/username")
                settings.remove("login/password")
                
            self.login_successful.emit(dict(user))
        else:
            self.login_error.setText("❌  Usuario o contraseña incorrectos.")

    # ── Register ─────────────────────────────────────────────────────────────

    def _make_register(self):
        w = self._clear_widget()
        L = QVBoxLayout(w)
        L.setContentsMargins(0, 0, 0, 0)
        L.setSpacing(0)
        L.addStretch()

        L.addWidget(self._h1("Crear cuenta"))
        L.addSpacing(6)
        L.addWidget(self._sub("Gratis · Sin límites · Sin correo"))
        L.addSpacing(28)

        for attr, label, ph, pwd in [
            ('reg_user',  "Usuario",                     "Elige un nombre",             False),
            ('reg_pass',  "Contraseña",                  "Mínimo 4 caracteres",         True),
            ('reg_pass2', "Confirmar contraseña",         "Repite tu contraseña",        True),
            ('reg_sq',    "Pregunta de seguridad",        "¿Nombre de tu primera mascota?", False),
            ('reg_sa',    "Respuesta (para recuperar cuenta)", "No distingue mayúsculas", False),
        ]:
            L.addWidget(self._field_label(label))
            L.addSpacing(4)
            field = self._input(ph, pwd=pwd)
            setattr(self, attr, field)
            L.addWidget(field)
            L.addSpacing(12)

        self.reg_error = self._err()
        L.addWidget(self.reg_error)
        L.addSpacing(16)

        btn = QPushButton("Crear cuenta")
        btn.setObjectName("AuthPrimary")
        btn.setFixedHeight(46)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._do_register)
        L.addWidget(btn)
        L.addSpacing(18)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._sub("¿Ya tienes cuenta?  "))
        btn2 = QPushButton("Inicia sesión")
        btn2.setObjectName("LinkButton")
        btn2.setCursor(Qt.CursorShape.PointingHandCursor)
        btn2.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        row.addWidget(btn2)
        row.addStretch()
        L.addLayout(row)
        L.addStretch()
        return w

    def _do_register(self):
        u  = self.reg_user.text().strip()
        p  = self.reg_pass.text()
        p2 = self.reg_pass2.text()
        sq = self.reg_sq.text().strip()
        sa = self.reg_sa.text().strip().lower()
        if not u:          self.reg_error.setText("❌  El nombre de usuario no puede estar vacío."); return
        if len(p) < 4:     self.reg_error.setText("❌  La contraseña debe tener al menos 4 caracteres."); return
        if p != p2:        self.reg_error.setText("❌  Las contraseñas no coinciden."); return
        if not sq or not sa: self.reg_error.setText("❌  Completa la pregunta de seguridad."); return
        ok, msg = db.register_user(u, p, sq, sa)
        if ok:
            QMessageBox.information(self, "¡Cuenta creada!", "Ya puedes iniciar sesión.")
            self.login_user.setText(u)
            self.stack.setCurrentIndex(0)
        else:
            self.reg_error.setText(f"❌  {msg}")

    # ── Forgot ────────────────────────────────────────────────────────────────

    def _make_forgot(self):
        w = self._clear_widget()
        L = QVBoxLayout(w)
        L.setContentsMargins(0, 0, 0, 0)
        L.setSpacing(0)
        L.addStretch()

        L.addWidget(self._h1("Recuperar contraseña"))
        L.addSpacing(6)
        L.addWidget(self._sub("Responde tu pregunta de seguridad"))
        L.addSpacing(28)

        L.addWidget(self._field_label("Usuario"))
        L.addSpacing(4)
        self.forgot_user = self._input("Tu nombre de usuario")
        self.forgot_user.editingFinished.connect(self._load_sq)
        L.addWidget(self.forgot_user)
        L.addSpacing(12)

        self.forgot_q_lbl = QLabel("")
        self.forgot_q_lbl.setStyleSheet("color:#98989d; font-style:italic; font-size:12px; background:transparent;")
        self.forgot_q_lbl.setWordWrap(True)
        L.addWidget(self.forgot_q_lbl)
        L.addSpacing(4)

        L.addWidget(self._field_label("Respuesta"))
        L.addSpacing(4)
        self.forgot_answer = self._input("Tu respuesta")
        L.addWidget(self.forgot_answer)
        L.addSpacing(12)

        L.addWidget(self._field_label("Nueva contraseña"))
        L.addSpacing(4)
        self.forgot_pass = self._input("Nueva contraseña", pwd=True)
        L.addWidget(self.forgot_pass)
        L.addSpacing(16)

        self.forgot_error = self._err()
        self.forgot_ok    = QLabel("")
        self.forgot_ok.setObjectName("SuccessLabel")
        self.forgot_ok.setStyleSheet("color:#30d158; font-size:12px; background:transparent;")
        L.addWidget(self.forgot_error)
        L.addWidget(self.forgot_ok)
        L.addSpacing(16)

        btn = QPushButton("Restablecer contraseña")
        btn.setObjectName("AuthPrimary")
        btn.setFixedHeight(46)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._do_reset)
        L.addWidget(btn)
        L.addSpacing(18)

        row = QHBoxLayout()
        row.addStretch()
        btn2 = QPushButton("← Volver al inicio de sesión")
        btn2.setObjectName("LinkButton")
        btn2.setCursor(Qt.CursorShape.PointingHandCursor)
        btn2.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        row.addWidget(btn2)
        row.addStretch()
        L.addLayout(row)
        L.addStretch()
        return w

    def _load_sq(self):
        q = db.get_security_question(self.forgot_user.text())
        self.forgot_q_lbl.setText(f"Pregunta: {q}" if q else "(usuario no encontrado o sin pregunta registrada)")

    def _do_reset(self):
        self.forgot_error.setText(""); self.forgot_ok.setText("")
        u = self.forgot_user.text().strip()
        a = self.forgot_answer.text().strip().lower()
        p = self.forgot_pass.text()
        if not u or not a or not p:
            self.forgot_error.setText("❌  Completa todos los campos."); return
        if len(p) < 4:
            self.forgot_error.setText("❌  La contraseña debe tener al menos 4 caracteres."); return
        ok, msg = db.reset_password(u, a, p)
        if ok:
            self.forgot_ok.setText("✅  Contraseña restablecida. Ya puedes iniciar sesión.")
        else:
            self.forgot_error.setText(f"❌  {msg}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clear_widget(self):
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        return w

    def _h1(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("AuthCardTitle")
        return lbl

    def _sub(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("AuthCardSub")
        return lbl

    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    def _input(self, placeholder="", pwd=False):
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        f.setFixedHeight(42)
        if pwd:
            f.setEchoMode(QLineEdit.EchoMode.Password)
        return f

    def _err(self):
        lbl = QLabel("")
        lbl.setObjectName("ErrorLabel")
        lbl.setWordWrap(True)
        lbl.setMinimumHeight(18)
        return lbl
