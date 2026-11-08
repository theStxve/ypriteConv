"""
App-wide look: neutral graphite / warm paper surfaces with one warm accent.
Flat surfaces, hairline borders, no gradients, no translucency.
"""
import os
import sys
import tempfile

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPalette
from PyQt6.QtWidgets import QApplication

DARK = dict(
    bg="#111111", surface="#18181A", raised="#1F1F22", hover="#26262A", pressed="#2E2E33",
    border="#29292D", border_strong="#3A3A40", text="#EDEDED", muted="#A1A1A7", subtle="#6F6F76",
    accent="#FF6A2B", accent_hover="#FF7D44", accent_pressed="#E85A1D", on_accent="#1A0C05",
    accent_soft="#2E1F17", success="#3DBE7A", error="#F0544F", warning="#E8B04A",
    success_soft="#16261D", error_soft="#2C1716",
)
LIGHT = dict(
    bg="#F4F3F0", surface="#FFFFFF", raised="#FAF9F7", hover="#EFEDE9", pressed="#E6E3DE",
    border="#E3E0DA", border_strong="#D0CCC4", text="#1A1A1A", muted="#66635E", subtle="#9C9890",
    accent="#E5531A", accent_hover="#EF6429", accent_pressed="#C9470F", on_accent="#FFFFFF",
    accent_soft="#FCEBE2", success="#1E9A5A", error="#D63A35", warning="#B07418",
    success_soft="#E4F4EA", error_soft="#FBE7E6",
)

# Category tints for file-type tiles (muted, distinct, readable in both themes)
CATEGORY_COLORS = {
    'image': "#3FA77A", 'video': "#E2703F", 'audio': "#C99A2E",
    'document': "#4F86D9", 'pdf': "#D0504A", 'unknown': "#8A8A90",
}

_current = dict(DARK)
_mode_setting = "System"


def colors():
    return _current


def is_dark():
    return _current is DARK or _current.get('bg') == DARK['bg']


def system_prefers_dark():
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return True


def _icon_files(c):
    """Small SVGs used by the stylesheet (combo arrow, checkbox tick)."""
    folder = os.path.join(tempfile.gettempdir(), "ypriteConvert-ui")
    os.makedirs(folder, exist_ok=True)
    files = {}
    svgs = {
        'chevron': f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{c["muted"]}" '
                   'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>',
        'check': f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{c["on_accent"]}" '
                 'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7"/></svg>',
        'dot': f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5.5" '
               f'fill="{c["on_accent"]}"/></svg>',
    }
    for name, svg in svgs.items():
        path = os.path.join(folder, f"{name}-{c['bg'].lstrip('#')}.svg")
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(svg)
        files[name] = path.replace('\\', '/')
    return files


def stylesheet(c):
    i = _icon_files(c)
    return f"""
* {{ outline: none; }}
QWidget {{ color: {c['text']}; font-size: 10pt; }}
QMainWindow, QDialog, #Root {{ background: {c['bg']}; }}
QToolTip {{ background: {c['raised']}; color: {c['text']}; border: 1px solid {c['border_strong']};
            padding: 6px 8px; border-radius: 6px; }}

/* ---------- text roles ---------- */
QLabel[role="title"] {{ font-size: 12.5pt; font-weight: 600; }}
QLabel[role="h1"] {{ font-size: 17pt; font-weight: 600; }}
QLabel[role="h2"] {{ font-size: 11pt; font-weight: 600; }}
QLabel[role="section"] {{ font-size: 8.5pt; font-weight: 600; color: {c['subtle']}; letter-spacing: 0.6px; }}
QLabel[role="muted"] {{ color: {c['muted']}; }}
QLabel[role="subtle"] {{ color: {c['subtle']}; font-size: 9pt; }}
QLabel[role="kbd"] {{ color: {c['muted']}; background: {c['raised']}; border: 1px solid {c['border']};
                     border-radius: 4px; padding: 1px 6px; font-size: 8.5pt; }}

/* ---------- surfaces ---------- */
#Header {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}
#BottomBar {{ background: {c['surface']}; border-top: 1px solid {c['border']}; }}
#Card {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 10px; }}
#DropZone {{ background: {c['surface']}; border: 1.5px dashed {c['border_strong']}; border-radius: 14px; }}
#DropZone[hover="true"] {{ border-color: {c['accent']}; background: {c['accent_soft']}; }}
#DropBadge {{ background: {c['accent_soft']}; border-radius: 28px; }}
#TypeTile {{ border-radius: 9px; }}

/* ---------- buttons ---------- */
QPushButton, QToolButton {{
    background: {c['raised']}; border: 1px solid {c['border']}; border-radius: 7px;
    padding: 7px 14px; color: {c['text']};
}}
QPushButton:hover, QToolButton:hover {{ background: {c['hover']}; border-color: {c['border_strong']}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {c['pressed']}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {c['subtle']}; background: {c['raised']}; border-color: {c['border']}; }}

QPushButton[kind="primary"] {{
    background: {c['accent']}; border: 1px solid {c['accent']}; color: {c['on_accent']};
    font-weight: 600; padding: 9px 22px;
}}
QPushButton[kind="primary"]:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QPushButton[kind="primary"]:pressed {{ background: {c['accent_pressed']}; }}
QPushButton[kind="primary"]:disabled {{ background: {c['hover']}; border-color: {c['hover']}; color: {c['subtle']}; }}
QPushButton[kind="danger"] {{ background: {c['error_soft']}; border-color: {c['error_soft']}; color: {c['error']};
                             font-weight: 600; padding: 9px 22px; }}
QPushButton[kind="danger"]:hover {{ border-color: {c['error']}; }}

QPushButton[kind="ghost"], QToolButton[kind="ghost"] {{ background: transparent; border-color: transparent; color: {c['muted']}; }}
QPushButton[kind="ghost"]:hover, QToolButton[kind="ghost"]:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton[kind="icon"], QToolButton[kind="icon"] {{ background: transparent; border: 1px solid transparent;
                            border-radius: 7px; padding: 6px; }}
QPushButton[kind="icon"]:hover, QToolButton[kind="icon"]:hover {{ background: {c['hover']}; }}
QPushButton[kind="update"] {{ background: {c['accent_soft']}; border: 1px solid {c['accent']}; color: {c['accent']};
                             font-weight: 600; padding: 5px 12px; border-radius: 13px; }}
QPushButton[kind="update"]:hover {{ background: {c['accent']}; color: {c['on_accent']}; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}

/* segmented control */
#Segmented {{ background: {c['raised']}; border: 1px solid {c['border']}; border-radius: 8px; }}
#Segmented QPushButton {{ background: transparent; border: none; border-radius: 6px; padding: 5px 12px;
                          color: {c['muted']}; }}
#Segmented QPushButton:hover {{ color: {c['text']}; }}
#Segmented QPushButton:checked {{ background: {c['surface']}; color: {c['text']}; font-weight: 600;
                                  border: 1px solid {c['border_strong']}; }}

/* ---------- inputs ---------- */
QComboBox, QLineEdit, QSpinBox {{
    background: {c['raised']}; border: 1px solid {c['border']}; border-radius: 7px;
    padding: 6px 10px; selection-background-color: {c['accent']}; selection-color: {c['on_accent']};
}}
QComboBox:hover, QLineEdit:hover {{ border-color: {c['border_strong']}; }}
QComboBox:focus, QLineEdit:focus {{ border-color: {c['accent']}; }}
QComboBox:disabled {{ color: {c['subtle']}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url("{i['chevron']}"); width: 13px; height: 13px; }}
QComboBox QAbstractItemView {{
    background: {c['raised']}; border: 1px solid {c['border_strong']}; border-radius: 8px; padding: 4px;
    selection-background-color: {c['hover']}; selection-color: {c['text']}; outline: none;
}}
QComboBox QAbstractItemView::item {{ min-height: 26px; padding: 0 8px; border-radius: 5px; }}

QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid {c['border_strong']};
                       background: {c['raised']}; }}
QCheckBox::indicator:hover {{ border-color: {c['accent']}; }}
QRadioButton {{ spacing: 10px; }}
QRadioButton::indicator {{ width: 16px; height: 16px; border-radius: 10px; border: 2px solid {c['border_strong']};
                          background: {c['raised']}; }}
QRadioButton::indicator:hover {{ border-color: {c['accent']}; }}
QRadioButton::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; image: url("{i['dot']}"); }}
QDoubleSpinBox {{ background: {c['raised']}; border: 1px solid {c['border']}; border-radius: 7px; padding: 5px 8px; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; image: url("{i['check']}"); }}

/* ---------- list ---------- */
#FileList {{ background: transparent; border: none; }}
#FileList::item {{ background: transparent; border: none; margin: 0; padding: 0; }}
#FileList::item:selected {{ background: transparent; }}
#FileRow {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 10px; }}
#FileRow[selected="true"] {{ border-color: {c['accent']}; }}
#FileRow:hover {{ border-color: {c['border_strong']}; }}

QProgressBar {{ background: {c['border']}; border: none; border-radius: 2px; max-height: 4px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 2px; }}

/* ---------- menus ---------- */
QMenu {{ background: {c['raised']}; border: 1px solid {c['border_strong']}; border-radius: 9px; padding: 5px; }}
QMenu::item {{ padding: 7px 26px 7px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {c['hover']}; }}
QMenu::item:disabled {{ color: {c['subtle']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 5px 6px; }}

/* ---------- scrollbars ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border_strong']}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['subtle']}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['border_strong']}; border-radius: 3px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; width: 0; }}

QTextBrowser {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 8px; }}
QListWidget#Plain {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 4px; }}
QListWidget#Plain::item {{ padding: 7px 8px; border-radius: 6px; }}
QListWidget#Plain::item:selected {{ background: {c['accent_soft']}; color: {c['text']}; }}
QListWidget#Plain::item:hover {{ background: {c['hover']}; }}
QGroupBox {{ border: 1px solid {c['border']}; border-radius: 10px; margin-top: 14px; padding: 12px 8px 8px 8px;
             background: {c['surface']}; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {c['muted']}; }}
QSplitter::handle {{ background: transparent; }}
QMessageBox {{ background: {c['bg']}; }}
"""


def _palette(c):
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: c['bg'], QPalette.ColorRole.WindowText: c['text'],
        QPalette.ColorRole.Base: c['surface'], QPalette.ColorRole.AlternateBase: c['raised'],
        QPalette.ColorRole.Text: c['text'], QPalette.ColorRole.Button: c['raised'],
        QPalette.ColorRole.ButtonText: c['text'], QPalette.ColorRole.Highlight: c['accent'],
        QPalette.ColorRole.HighlightedText: c['on_accent'], QPalette.ColorRole.ToolTipBase: c['raised'],
        QPalette.ColorRole.ToolTipText: c['text'], QPalette.ColorRole.PlaceholderText: c['subtle'],
        QPalette.ColorRole.Link: c['accent'], QPalette.ColorRole.Mid: c['border'],
    }
    for role, col in roles.items():
        p.setColor(role, QColor(col))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(c['subtle']))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(c['subtle']))
    return p


def apply(mode="System"):
    """Apply theme to the whole app. mode: System / Light / Dark."""
    global _current, _mode_setting
    _mode_setting = mode
    dark = system_prefers_dark() if mode == "System" else mode == "Dark"
    _current = DARK if dark else LIGHT

    app = QApplication.instance()
    app.setStyle("Fusion")
    font = QFont("Segoe UI Variable Text")
    if not font.exactMatch():
        font = QFont("Segoe UI")
    font.setPointSizeF(10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)
    app.setPalette(_palette(_current))
    app.setStyleSheet(stylesheet(_current))

    for w in app.topLevelWidgets():
        set_dark_titlebar(w, dark)
    return dark


def current_mode():
    return _mode_setting


def set_dark_titlebar(widget, dark=None):
    """Match the Windows title bar to the theme (Windows 10 1809+/11)."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        if dark is None:
            dark = is_dark()
        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new / old builds)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
        # Caption colour = window background for a seamless header (Windows 11)
        bg = QColor(_current['bg'])
        colorref = ctypes.c_int(bg.red() | (bg.green() << 8) | (bg.blue() << 16))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref), ctypes.sizeof(colorref))
    except Exception:
        pass


def repolish(widget):
    """Re-apply stylesheet after changing a dynamic property."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
