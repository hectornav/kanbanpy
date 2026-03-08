"""
styles.py — Kanbanpy Pro · Apple-inspired macOS dark mode design system
─────────────────────────────────────────────────────────────────────────
Colors from Apple HIG (dark):
  Background layers: #000000 / #1c1c1e / #2c2c2e / #3a3a3c
  System colors:     blue  #0a84ff  green #30d158  orange #ff9f0a  red #ff453a
  Text:              primary #ffffff  secondary #98989d
  Separators:        rgba(84,84,88,0.65)
"""

_APPLE_FONT = "'SF Pro Display', 'SF Pro', 'Helvetica Neue', Helvetica, Arial, sans-serif"

STYLESHEET = f"""
/* ── Reset ──────────────────────────────────────────────────────────────── */
* {{
    font-family: {_APPLE_FONT};
    font-size: 13px;
}}

/* Transparent labels everywhere by default */
QLabel {{
    background: transparent;
    color: #ffffff;
}}

/* ── Root window bg ─────────────────────────────────────────────────────── */
/* ── Root window bg ─────────────────────────────────────────────────────── */
QMainWindow, QDialog {{ background-color: #1c1c1e; color: #ffffff; }}
QDialog QLabel {{ color: #e5e5ea; background: transparent; }}

/* ── App header ─────────────────────────────────────────────────────────── */
#AppHeader {{
    background-color: #1c1c1e;
    border-bottom: 1px solid rgba(84,84,88,0.65);
}}
#HeaderTitle {{
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.3px;
    background: transparent;
}}
#HeaderUser {{
    font-size: 12px;
    color: #98989d;
    background: transparent;
}}
QPushButton#LogoutBtn {{
    background: rgba(255,255,255,0.07);
    color: #98989d;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 7px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#LogoutBtn:hover {{ background: rgba(255,255,255,0.12); color: #e5e5ea; }}

/* ── Board body ─────────────────────────────────────────────────────────── */
#BoardBody {{ background-color: #000000; }}

/* ── Column panel (uses inline stylesheet per-column in views.py) ─────── */
/* CountBadge */
#CountBadge {{
    background: rgba(255,255,255,0.10);
    color: #98989d;
    border-radius: 8px;
    padding: 0px 8px;
    font-size: 11px;
    font-weight: 600;
    min-width: 20px;
    qproperty-alignment: AlignCenter;
}}

/* ── List widget ────────────────────────────────────────────────────────── */
QListWidget {{
    background: transparent;
    border: none;
    outline: 0;
    padding: 4px 2px;
}}
QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0;
    margin-bottom: 8px;
}}
QListWidget::item:selected {{ background: transparent; border: none; }}

/* ── Task Card ──────────────────────────────────────────────────────────── */
#TaskCard {{
    background-color: #2c2c2e;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
}}
#TaskCard:hover {{
    background-color: #3a3a3c;
    border: 1px solid rgba(255, 255, 255, 0.15);
}}

/* DnD drop indicator */
QListWidget::indicator {{
    background-color: #0a84ff;
    height: 4px;
}}

/* ── Priority chips (Apple system colors) ─────────────────────────────── */
#Priority_High   {{ background:#3d0e0a; color:#ff453a; border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700; }}
#Priority_Medium {{ background:#3d280a; color:#ff9f0a; border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700; }}
#Priority_Low    {{ background:#0a2d16; color:#30d158; border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700; }}

/* ── Tags, shared badge ─────────────────────────────────────────────────── */
#TagLabel {{
    background: rgba(10,132,255,0.15);
    color: #0a84ff;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
#SharedBadge {{
    background: rgba(255,159,10,0.15);
    color: #ff9f0a;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}

/* ── Footer bar ─────────────────────────────────────────────────────────── */
#FooterBar {{
    background-color: #1c1c1e;
    border-top: 1px solid rgba(84,84,88,0.65);
}}
QPushButton#AddBtn {{
    background-color: #0a84ff;
    color: #ffffff;
    border: none;
    border-radius: 9px;
    padding: 9px 24px;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: -0.2px;
}}
QPushButton#AddBtn:hover   {{ background-color: #3395ff; }}
QPushButton#AddBtn:pressed {{ background-color: #0060c0; }}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}
QScrollBar::handle:vertical {{ background: rgba(84,84,88,0.60); min-height: 20px; border-radius: 3px; }}
QScrollBar::handle:vertical:hover {{ background: #0a84ff; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Context menu ───────────────────────────────────────────────────────── */
QMenu {{
    background-color: #2c2c2e;
    border: 1px solid rgba(84,84,88,0.65);
    border-radius: 10px;
    padding: 5px;
    color: #ffffff;
}}
QMenu::item {{ padding: 7px 18px; border-radius: 6px; color: #ffffff; background: transparent; }}
QMenu::item:selected {{ background: rgba(10,132,255,0.25); color: #0a84ff; }}
QMenu::separator {{ background: rgba(84,84,88,0.65); height: 1px; margin: 4px 8px; }}

/* ── Dialog inputs ──────────────────────────────────────────────────────── */
QDialog QLineEdit, QDialog QTextEdit, QDialog QComboBox {{
    background-color: #2c2c2e;
    border: 1px solid rgba(84,84,88,0.65);
    border-radius: 8px;
    padding: 9px 11px;
    color: #ffffff;
    font-size: 13px;
    selection-background-color: #0a84ff;
    selection-color: #ffffff;
}}
QDialog QLineEdit:focus, QDialog QTextEdit:focus, QDialog QComboBox:focus {{
    border: 1px solid #0a84ff;
    background-color: #3a3a3c;
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: #2c2c2e;
    border: 1px solid rgba(84,84,88,0.65);
    color: #ffffff;
    selection-background-color: rgba(10,132,255,0.30);
    selection-color: #ffffff;
}}

/* ── Dialog generic button ──────────────────────────────────────────────── */
QDialog QPushButton {{
    background: rgba(120,120,128,0.20);
    color: #ffffff;
    border: 1px solid rgba(84,84,88,0.65);
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 500;
}}
QDialog QPushButton:hover   {{ background: rgba(120,120,128,0.30); }}
QDialog QPushButton:pressed {{ background: rgba(120,120,128,0.40); }}

/* Primary action button in dialogs */
QDialog QPushButton#PrimaryButton {{
    background: #0a84ff;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 22px;
    font-weight: 600;
}}
QDialog QPushButton#PrimaryButton:hover   {{ background: #3395ff; }}
QDialog QPushButton#PrimaryButton:pressed {{ background: #0060c0; }}

/* ── Checkbox ───────────────────────────────────────────────────────────── */
QCheckBox {{ font-size: 13px; color: #e5e5ea; spacing: 7px; background: transparent; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1.5px solid rgba(84,84,88,0.80);
    border-radius: 5px;
    background: rgba(120,120,128,0.15);
}}
QCheckBox::indicator:checked {{
    background-color: #0a84ff;
    border-color: #0a84ff;
}}

/* ── Auth window ────────────────────────────────────────────────────────── */
QWidget#AuthWindow {{
    background-color: #000000;
}}
/* Left brand panel */
QFrame#BrandPanel {{
    background: #1c1c1e;
    border-right: 1px solid rgba(84,84,88,0.50);
}}
/* Right form card */
QFrame#AuthCard {{
    background-color: #1c1c1e;
}}
#AuthCard QLabel {{ color: #e5e5ea; background: transparent; }}
#AuthCardTitle   {{ font-size: 26px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px; background: transparent; }}
#AuthCardSub     {{ font-size: 13px; color: #98989d; background: transparent; }}
#FieldLabel      {{ color: #98989d; font-weight: 500; font-size: 12px; background: transparent; }}
#ErrorLabel      {{ color: #ff453a; font-size: 12px; font-weight: 500; background: transparent; }}
#SuccessLabel    {{ color: #30d158; font-size: 12px; font-weight: 500; background: transparent; }}
#AppTagline      {{ font-size: 24px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px; background: transparent; }}
#AppSubTagline   {{ font-size: 13px; color: #98989d; background: transparent; }}

/* Auth inputs — inside the brand-dark context */
QWidget#AuthWindow QLineEdit {{
    background: rgba(120,120,128,0.12);
    border: 1px solid rgba(84,84,88,0.60);
    border-radius: 9px;
    padding: 0 13px;
    color: #ffffff;
    font-size: 13px;
    selection-background-color: #0a84ff;
}}
QWidget#AuthWindow QLineEdit:focus {{
    border: 1px solid #0a84ff;
    background: rgba(10,132,255,0.10);
}}

/* Auth primary button */
QPushButton#AuthPrimary {{
    background: #0a84ff;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 11px 0;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.2px;
}}
QPushButton#AuthPrimary:hover   {{ background: #3395ff; }}
QPushButton#AuthPrimary:pressed {{ background: #0060c0; }}

/* Auth link button */
QPushButton#LinkButton {{
    background: transparent;
    border: none;
    color: #0a84ff;
    font-weight: 500;
    font-size: 13px;
    padding: 0;
}}
QPushButton#LinkButton:hover {{ color: #3395ff; }}
"""