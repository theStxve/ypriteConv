import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QTransform
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QLineEdit,
                             QCheckBox, QDoubleSpinBox, QTextBrowser, QListWidget, QListWidgetItem,
                             QAbstractItemView, QMessageBox, QFrame, QProgressBar, QRadioButton, QButtonGroup)

from converters.video_converter import DEFAULT_VIDEO_OPTIONS
from modules.media import parse_time, format_time
from . import theme
from .i18n import tr
from .widgets import label, button, Segmented


class FuncThread(QThread):
    """Run fn(*args) off the UI thread."""
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn, self.args = fn, args

    def run(self):
        try:
            self.done.emit(self.fn(*self.args))
        except Exception as e:
            self.failed.emit(str(e))


def _footer(dialog, primary_text, on_primary, extra_left=None):
    bar = QFrame()
    bar.setObjectName("BottomBar")
    h = QHBoxLayout(bar)
    h.setContentsMargins(20, 12, 20, 12)
    if extra_left:
        h.addWidget(extra_left)
    h.addStretch()
    cancel = button(tr("Cancel"))
    cancel.clicked.connect(dialog.reject)
    h.addWidget(cancel)
    ok = button(primary_text, "primary")
    ok.clicked.connect(on_primary)
    ok.setDefault(True)
    h.addWidget(ok)
    return bar, ok


# ====================================================================== video
SIZE_PRESETS = [(0, "Off"), (10, "10 MB"), (25, "25 MB"), (50, "50 MB"), (100, "100 MB"), (-1, "Custom…")]
HEIGHTS = [(0, "Original"), (2160, "4K (2160p)"), (1080, "1080p"), (720, "720p"), (480, "480p"), (360, "360p")]


class VideoOptionsDialog(QDialog):
    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.row = row
        self.setWindowTitle(tr("Video options"))
        self.setMinimumWidth(560)
        opts = {**DEFAULT_VIDEO_OPTIONS, **(row.video_opts or {})}
        self.duration = row.duration

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QVBoxLayout()
        body.setContentsMargins(24, 20, 24, 18)
        body.setSpacing(14)
        outer.addLayout(body)

        top = QHBoxLayout()
        top.setSpacing(16)
        self.preview = QLabel()
        self.preview.setFixedSize(150, 150)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setObjectName("Card")
        top.addWidget(self.preview)
        info = QVBoxLayout()
        info.addWidget(label(tr("Video options"), "h1"))
        name = label(os.path.basename(row.path), "muted")
        name.setWordWrap(True)
        info.addWidget(name)
        if self.duration:
            info.addWidget(label(tr("Length: {t}", t=format_time(self.duration)), "subtle"))
        info.addStretch()
        top.addLayout(info, 1)
        body.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        r = 0

        grid.addWidget(label(tr("Rotate")), r, 0)
        self.rotate = Segmented([("none", tr("None")), ("cw", tr("90° right")), ("ccw", tr("90° left")),
                                 ("180", tr("180°")), ("hflip", tr("Mirror"))], opts['rotate'])
        self.rotate.changed.connect(lambda _: self._update_preview())
        grid.addWidget(self.rotate, r, 1, 1, 3)
        r += 1

        grid.addWidget(label(tr("Resolution")), r, 0)
        self.height = QComboBox()
        for value, text in HEIGHTS:
            self.height.addItem(tr(text), value)
        self.height.setCurrentIndex(max(0, self.height.findData(opts['height'])))
        grid.addWidget(self.height, r, 1)
        r += 1

        grid.addWidget(label(tr("Max. file size")), r, 0)
        self.size = QComboBox()
        for value, text in SIZE_PRESETS:
            self.size.addItem(tr(text), value)
        self.custom_mb = QDoubleSpinBox()
        self.custom_mb.setRange(1, 100000)
        self.custom_mb.setDecimals(1)
        self.custom_mb.setSuffix(" MB")
        self.custom_mb.setToolTip(tr("Size in MB"))
        mb = opts['target_mb'] or 0
        idx = self.size.findData(int(mb)) if mb in (0, 10, 25, 50, 100) else self.size.findData(-1)
        self.size.setCurrentIndex(max(0, idx))
        self.custom_mb.setValue(mb or 20)
        self.size.currentIndexChanged.connect(lambda _: self.custom_mb.setVisible(self.size.currentData() == -1))
        self.custom_mb.setVisible(self.size.currentData() == -1)
        grid.addWidget(self.size, r, 1)
        grid.addWidget(self.custom_mb, r, 2)
        r += 1

        grid.addWidget(label(tr("Trim")), r, 0)
        trim = QHBoxLayout()
        trim.setSpacing(8)
        self.start = QLineEdit(format_time(opts['trim_start']) if opts['trim_start'] else "")
        self.start.setPlaceholderText(tr("Start") + "  0:00")
        self.end = QLineEdit(format_time(opts['trim_end']) if opts['trim_end'] else "")
        self.end.setPlaceholderText(tr("End") + (f"  {format_time(self.duration)}" if self.duration else ""))
        for e in (self.start, self.end):
            e.setFixedWidth(110)
        trim.addWidget(self.start)
        trim.addWidget(label("–", "muted"))
        trim.addWidget(self.end)
        trim.addStretch()
        grid.addLayout(trim, r, 1, 1, 3)
        r += 1

        self.no_audio = QCheckBox(tr("Remove audio"))
        self.no_audio.setChecked(bool(opts['remove_audio']))
        grid.addWidget(self.no_audio, r, 1, 1, 3)
        grid.setColumnStretch(3, 1)
        body.addLayout(grid)

        self.apply_all = QCheckBox(tr("Apply to all videos in the list"))
        body.addWidget(self.apply_all)

        reset = button(tr("Reset"), "ghost")
        reset.clicked.connect(self._reset)
        bar, _ = _footer(self, tr("Apply"), self._accept, reset)
        outer.addWidget(bar)
        self.result_opts = None
        self._update_preview()

    def _update_preview(self):
        pm = self.row.thumb_pixmap(150)
        if pm is None or pm.isNull():
            self.preview.setText("▶")
            return
        t = QTransform()
        rot = self.rotate.value()
        if rot == 'cw':
            t.rotate(90)
        elif rot == 'ccw':
            t.rotate(-90)
        elif rot == '180':
            t.rotate(180)
        elif rot == 'hflip':
            t.scale(-1, 1)
        self.preview.setPixmap(pm.transformed(t, Qt.TransformationMode.SmoothTransformation))

    def _reset(self):
        self.rotate.set_value('none')
        self.height.setCurrentIndex(0)
        self.size.setCurrentIndex(0)
        self.start.clear()
        self.end.clear()
        self.no_audio.setChecked(False)
        self._update_preview()

    def _accept(self):
        try:
            start = parse_time(self.start.text())
        except ValueError:
            QMessageBox.warning(self, tr("Trim"), tr("Invalid time: {t}", t=self.start.text()))
            return
        try:
            end = parse_time(self.end.text())
        except ValueError:
            QMessageBox.warning(self, tr("Trim"), tr("Invalid time: {t}", t=self.end.text()))
            return
        if start is not None and end is not None and end <= start:
            QMessageBox.warning(self, tr("Trim"), tr("End must be after start."))
            return
        if self.duration and end and end >= self.duration - 0.05:
            end = None   # trimming to the full length = no trim
        mb = self.size.currentData()
        if mb == -1:
            mb = self.custom_mb.value()
        self.result_opts = {
            'rotate': self.rotate.value(),
            'height': self.height.currentData(),
            'target_mb': mb or 0,
            'trim_start': start or None,
            'trim_end': end,
            'remove_audio': self.no_audio.isChecked(),
        }
        self.accept()


def video_summary(opts):
    """Short text for the file row, e.g. '720p · ≤ 25 MB · trimmed'."""
    if not opts:
        return ""
    parts = []
    if opts.get('rotate', 'none') != 'none':
        parts.append(tr("rotated"))
    if opts.get('height'):
        parts.append(f"{opts['height']}p")
    if opts.get('target_mb'):
        parts.append(tr("≤ {mb} MB", mb=f"{opts['target_mb']:g}"))
    if opts.get('trim_start') or opts.get('trim_end'):
        parts.append(tr("trimmed"))
    if opts.get('remove_audio'):
        parts.append(tr("no audio"))
    return " · ".join(parts)


# ====================================================================== combine
class CombinePdfDialog(QDialog):
    def __init__(self, paths, default_dir, quality, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Combine into one PDF"))
        self.setMinimumSize(520, 520)
        self.default_dir = default_dir
        self.quality = quality
        self.created = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QVBoxLayout()
        body.setContentsMargins(24, 20, 24, 16)
        body.setSpacing(10)
        outer.addLayout(body, 1)

        body.addWidget(label(tr("Combine into one PDF"), "h1"))
        body.addWidget(label(tr("Drag to change the order."), "muted"))
        self.list = QListWidget()
        self.list.setObjectName("Plain")
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        for p in paths:
            item = QListWidgetItem(os.path.basename(p))
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setToolTip(p)
            self.list.addItem(item)
        body.addWidget(self.list, 1)

        row = QHBoxLayout()
        row.addWidget(label(tr("File name")))
        base = os.path.splitext(os.path.basename(paths[0]))[0] if paths else "combined"
        self.name = QLineEdit(f"{base} combined.pdf" if len(paths) > 1 else f"{base}.pdf")
        row.addWidget(self.name, 1)
        body.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(label(tr("Page size")))
        row.addStretch()
        self.page = Segmented([('fit', tr("Fit to image")), ('a4', tr("A4"))], 'fit')
        row.addWidget(self.page)
        body.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        body.addWidget(self.progress)

        bar, self.ok = _footer(self, tr("Combine"), self._run)
        outer.addWidget(bar)

    def _run(self):
        from modules.pdf_tools import combine
        name = self.name.text().strip() or "combined.pdf"
        if not name.lower().endswith('.pdf'):
            name += '.pdf'
        dest = os.path.join(self.default_dir, name)
        n = 1
        while os.path.exists(dest):
            dest = os.path.join(self.default_dir, f"{os.path.splitext(name)[0]} ({n}).pdf")
            n += 1
        paths = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]
        self.ok.setEnabled(False)
        self.ok.setText(tr("Combining…"))
        self.progress.setRange(0, 0)
        self.progress.show()
        os.makedirs(self.default_dir, exist_ok=True)
        self.thread = FuncThread(combine, paths, dest, self.page.value(), self.quality)
        self.thread.done.connect(self._done)
        self.thread.failed.connect(self._failed)
        self.thread.start()

    def _done(self, dest):
        self.created = dest
        self.accept()

    def _failed(self, err):
        self.progress.hide()
        self.ok.setEnabled(True)
        self.ok.setText(tr("Combine"))
        QMessageBox.warning(self, tr("Combine into one PDF"), tr("Couldn't create the PDF:\n{err}", err=err))


# ====================================================================== text / changelog
class MarkdownDialog(QDialog):
    def __init__(self, title, subtitle, markdown, button_text=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(540, 460)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 20)
        v.setSpacing(8)
        v.addWidget(label(title, "h1"))
        if subtitle:
            s = label(subtitle, "muted")
            s.setWordWrap(True)
            v.addWidget(s)
        text = QTextBrowser()
        text.setOpenExternalLinks(True)
        text.setMarkdown(markdown or tr("_No release notes._"))
        v.addWidget(text, 1)
        row = QHBoxLayout()
        row.addStretch()
        ok = button(button_text or tr("Close"), "primary")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        v.addLayout(row)


# ====================================================================== onboarding
class OnboardingDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        from app_info import APP_NAME
        from modules import shell_integration
        self.cfg = config
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        v = QVBoxLayout()
        v.setContentsMargins(32, 28, 32, 22)
        v.setSpacing(10)
        outer.addLayout(v)

        from PyQt6.QtGui import QIcon
        from modules.paths import resource
        logo = QLabel()
        logo.setPixmap(QIcon(resource('assets', 'icon.ico')).pixmap(56, 56))
        v.addWidget(logo)
        v.addSpacing(4)
        v.addWidget(label(tr("Welcome to ypriteConvert"), "h1"))
        sub = label(tr("Convert images, videos, audio and documents — fast, private, right on your PC."), "muted")
        sub.setWordWrap(True)
        v.addWidget(sub)
        v.addSpacing(14)

        v.addWidget(label(tr("Where should converted files go?").upper(), "section"))
        self.where = QButtonGroup(self)
        self.next_to = QRadioButton(tr("Next to the original file"))
        self.folder = QRadioButton(tr("Into one folder"))
        for b in (self.next_to, self.folder):
            self.where.addButton(b)
            v.addWidget(b)
        (self.folder if config.get("output_mode") == "folder" else self.next_to).setChecked(True)
        v.addSpacing(10)

        v.addWidget(label(tr("APPEARANCE"), "section"))
        row = QHBoxLayout()
        row.addWidget(label(tr("Theme")))
        row.addStretch()
        self.theme_seg = Segmented([("System", tr("System")), ("Light", tr("Light")), ("Dark", tr("Dark"))],
                                   config.get("theme_mode"))
        self.theme_seg.changed.connect(self._preview_theme)
        row.addWidget(self.theme_seg)
        v.addLayout(row)
        v.addSpacing(10)

        self.ctx = QCheckBox(tr("Add “Convert with ypriteConvert” to the Explorer right-click menu"))
        self.ctx.setVisible(shell_integration.available())
        self.ctx.setChecked(shell_integration.is_enabled() or shell_integration.available())
        v.addWidget(self.ctx)
        self.updates = QCheckBox(tr("Check for updates automatically"))
        self.updates.setChecked(bool(config.get("auto_update")))
        v.addWidget(self.updates)
        v.addSpacing(6)
        tip = label(tr("Tip: drop files anywhere in the window, or press Ctrl+V to paste."), "subtle")
        tip.setWordWrap(True)
        v.addWidget(tip)

        bar = QFrame()
        bar.setObjectName("BottomBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 12, 20, 12)
        h.addStretch()
        go = button(tr("Get started"), "primary")
        go.clicked.connect(self._finish)
        h.addWidget(go)
        outer.addWidget(bar)

    def _preview_theme(self, mode):
        theme.apply(mode)
        theme.set_dark_titlebar(self)
        if self.parent():
            self.parent().refresh_theme()

    def _finish(self):
        from modules import shell_integration
        from PyQt6.QtWidgets import QFileDialog
        if self.folder.isChecked():
            folder = QFileDialog.getExistingDirectory(self, tr("Choose output folder"),
                                                      self.cfg.get("default_output_path") or os.path.expanduser("~"))
            if folder:
                self.cfg.set("default_output_path", folder)
                self.cfg.set("output_mode", "folder")
            else:
                self.cfg.set("output_mode", "source")
        else:
            self.cfg.set("output_mode", "source")
        self.cfg.set("theme_mode", self.theme_seg.value())
        self.cfg.set("auto_update", self.updates.isChecked())
        if shell_integration.available():
            try:
                if self.ctx.isChecked():
                    shell_integration.enable(tr("Convert with ypriteConvert"))
                else:
                    shell_integration.disable()
            except OSError:
                pass
        self.cfg.set("onboarded", True)
        self.accept()
