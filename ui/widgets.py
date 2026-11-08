import os

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFontMetrics, QColor, QIcon
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
                             QComboBox, QButtonGroup, QFrame, QSizePolicy, QToolButton)

from modules.format_rules import FormatRules
from . import icons, theme


def label(text="", role=None, parent=None):
    lbl = QLabel(text, parent)
    if role:
        lbl.setProperty("role", role)
    return lbl


def button(text="", kind=None, icon_name=None, icon_color=None, tooltip=None, size=16):
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if icon_name:
        b.setIcon(icons.icon(icon_name, icon_color or theme.colors()['muted'], size))
        b.setIconSize(QSize(size, size))
    if tooltip:
        b.setToolTip(tooltip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def human_size(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f"{n:.0f} {unit}" if unit == 'B' else f"{n:.1f} {unit}"
        n /= 1024


def category_of(fmt):
    if fmt == 'pdf':
        return 'pdf'
    return FormatRules.get_category(fmt)


class Segmented(QFrame):
    """Pill-style segmented control."""
    changed = pyqtSignal(str)

    def __init__(self, options, current=None):
        super().__init__()
        self.setObjectName("Segmented")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self._values = {}
        for value, text in options:
            b = QPushButton(text)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(b)
            self._values[b] = value
            lay.addWidget(b)
            if value == current:
                b.setChecked(True)
        if not self.group.checkedButton() and self._values:
            next(iter(self._values)).setChecked(True)
        self.group.buttonClicked.connect(lambda b: self.changed.emit(self._values[b]))

    def value(self):
        return self._values.get(self.group.checkedButton())

    def set_value(self, value):
        for b, v in self._values.items():
            if v == value:
                b.setChecked(True)


class DropZone(QFrame):
    """Big empty-state target: drop files here or click to browse."""
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(320)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(6)

        self.badge = QLabel()
        self.badge.setObjectName("DropBadge")
        self.badge.setFixedSize(56, 56)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(10)

        self.title = label("Drop files to convert", "h1")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title)
        self.sub = label("or click to browse — folders and ZIPs work too", "muted")
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.sub)
        lay.addSpacing(18)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        chips.addStretch()
        for name, text in (('image', 'Images'), ('video', 'Video'), ('audio', 'Audio'),
                           ('document', 'Documents'), ('pdf', 'PDF')):
            chips.addWidget(self._chip(name, text))
        chips.addStretch()
        lay.addLayout(chips)
        self.refresh_icons()

    def _chip(self, name, text):
        w = QFrame()
        w.setObjectName("Card")
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 5, 12, 5)
        h.setSpacing(6)
        ic = QLabel()
        ic.setProperty("chipicon", name)
        h.addWidget(ic)
        h.addWidget(label(text, "muted"))
        return w

    def refresh_icons(self):
        c = theme.colors()
        self.badge.setPixmap(icons.pixmap('upload', c['accent'], 26, 2))
        for ic in self.findChildren(QLabel):
            name = ic.property("chipicon")
            if name:
                ic.setPixmap(icons.pixmap(name, theme.CATEGORY_COLORS[name], 15))

    def set_hover(self, on):
        self.setProperty("hover", "true" if on else "false")
        theme.repolish(self)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class ElidedLabel(QLabel):
    def __init__(self, text="", role=None):
        super().__init__()
        self._full = text
        if role:
            self.setProperty("role", role)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(40)

    def setText(self, text):
        self._full = text
        self._elide()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()

    def _elide(self):
        fm = QFontMetrics(self.font())
        super().setText(fm.elidedText(self._full, Qt.TextElideMode.ElideMiddle, max(self.width(), 40)))


STATUS_STYLE = {
    # status: (text, color key, icon)
    "Ready": ("Ready", 'subtle', None),
    "Queued": ("Queued", 'muted', None),
    "Running": ("Converting…", 'accent', None),
    "Done": ("Done", 'success', 'check'),
    "Error": ("Failed", 'error', 'alert'),
    "Cancelled": ("Cancelled", 'subtle', None),
    "Unsupported": ("Unsupported", 'subtle', None),
}


class FileRow(QFrame):
    """One file in the queue: type tile, name/details, target format, status, actions."""
    remove_requested = pyqtSignal(object)
    reveal_requested = pyqtSignal(object)
    details_requested = pyqtSignal(object)

    def __init__(self, path, detection, options):
        super().__init__()
        self.setObjectName("FileRow")
        self.path = path
        self.det = detection
        self.options = options
        self.status = "Ready" if options else "Unsupported"
        self.message = ""
        self.output = None
        self.setFixedHeight(64)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 10, 10)
        lay.setSpacing(12)

        self.tile = QLabel()
        self.tile.setObjectName("TypeTile")
        self.tile.setFixedSize(40, 40)
        self.tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.tile)

        text = QVBoxLayout()
        text.setSpacing(1)
        self.name = ElidedLabel(os.path.basename(path))
        self.name.setStyleSheet("font-weight: 600;")
        self.name.setToolTip(path)
        self.details = ElidedLabel("", "subtle")
        text.addWidget(self.name)
        text.addWidget(self.details)
        lay.addLayout(text, 1)

        self.arrow = QLabel()
        lay.addWidget(self.arrow)

        self.combo = QComboBox()
        self.combo.setFixedWidth(132)
        self.combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for fmt, text_ in options:
            self.combo.addItem(text_, fmt)
        if not options:
            self.combo.addItem("—")
            self.combo.setEnabled(False)
        lay.addWidget(self.combo)

        self.status_btn = QPushButton()
        self.status_btn.setProperty("kind", "ghost")
        self.status_btn.setFixedWidth(118)
        self.status_btn.setStyleSheet("text-align: left; padding-left: 8px;")
        self.status_btn.clicked.connect(self._status_clicked)
        lay.addWidget(self.status_btn)

        self.remove_btn = QPushButton()
        self.remove_btn.setProperty("kind", "icon")
        self.remove_btn.setToolTip("Remove from list")
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        lay.addWidget(self.remove_btn)

        self._fill_details()
        self.refresh_theme()

    # -- data
    def target(self):
        return self.combo.currentData() if self.options else None

    def set_target(self, fmt):
        i = self.combo.findData(fmt)
        if i >= 0:
            self.combo.setCurrentIndex(i)
            return True
        return False

    def _fill_details(self):
        try:
            size = human_size(os.path.getsize(self.path))
        except OSError:
            size = "?"
        kind = (self.det.effective or 'unknown').upper()
        parts = [kind, size]
        if self.det.mismatch:
            parts[0] = f"{self.det.real.upper()} detected"
            parts.append(f"saved as .{self.det.ext}" if self.det.ext else "no extension")
        elif not self.options:
            parts.append("can't be converted")
        parent = os.path.basename(os.path.dirname(self.path))
        if parent:
            parts.append(parent)
        self.details.setText("  ·  ".join(parts))
        if self.det.mismatch:
            self.details.setToolTip(f"The content is {self.det.label or self.det.real.upper()}, "
                                    f"even though the file is named .{self.det.ext or '(none)'}.\n"
                                    f"Pick “{self.det.real} · restore” to just fix the extension.")

    # -- status
    def set_status(self, status, message=""):
        self.status = status
        self.message = message or ""
        self._paint_status()

    def _paint_status(self):
        c = theme.colors()
        text, key, ic = STATUS_STYLE.get(self.status, (self.status, 'muted', None))
        color = c[key]
        if self.status == "Done" and self.output:
            text = "Done · Show"
        self.status_btn.setText(text)
        self.status_btn.setIcon(icons.icon(ic, color, 15) if ic else QIcon())
        self.status_btn.setStyleSheet(f"text-align: left; padding-left: 8px; color: {color};"
                                      + (" font-weight: 600;" if self.status in ("Done", "Error", "Running") else ""))
        tip = self.message
        if self.status == "Error":
            tip = (tip + "\n\nClick for details") if tip else "Click for details"
        elif self.status == "Done" and self.output:
            tip = f"{self.message}\n\nClick to show in Explorer:\n{self.output}".strip()
        self.status_btn.setToolTip(tip)
        clickable = self.status in ("Done", "Error")
        self.status_btn.setCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)

    def _status_clicked(self):
        if self.status == "Done" and self.output:
            self.reveal_requested.emit(self)
        elif self.status == "Error":
            self.details_requested.emit(self)

    def set_busy(self, busy, pipeline_mode=False):
        self.combo.setEnabled(bool(self.options) and not busy and not pipeline_mode)
        self.remove_btn.setEnabled(not busy)

    def set_selected(self, on):
        self.setProperty("selected", "true" if on else "false")
        theme.repolish(self)

    def refresh_theme(self):
        c = theme.colors()
        cat = category_of(self.det.effective) if self.det.effective else 'unknown'
        tint = theme.CATEGORY_COLORS.get(cat, theme.CATEGORY_COLORS['unknown'])
        bg = QColor(tint)
        bg.setAlpha(38 if theme.is_dark() else 30)
        self.tile.setStyleSheet(f"background: rgba({bg.red()},{bg.green()},{bg.blue()},{bg.alpha()}); border-radius: 9px;")
        self.tile.setPixmap(icons.pixmap(cat if cat in ('image', 'video', 'audio', 'document', 'pdf') else 'unknown',
                                         tint, 20))
        self.arrow.setPixmap(icons.pixmap('arrow-right', c['subtle'], 16))
        self.remove_btn.setIcon(icons.icon('x', c['subtle'], 16))
        self._paint_status()
