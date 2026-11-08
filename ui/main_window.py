import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime

from PyQt6.QtCore import Qt, QSize, QTimer, QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QIcon, QGuiApplication
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QFileDialog, QMessageBox, QStackedWidget, QListWidget, QListWidgetItem,
                             QProgressBar, QToolButton, QMenu, QApplication, QAbstractItemView, QFrame)

from app_info import APP_NAME, VERSION
from modules.config_manager import ConfigManager
from modules.file_detect import detect, target_options
from modules.format_rules import FormatRules
from modules.paths import resource
from modules.worker import ConversionWorker
from . import icons, theme
from .i18n import tr, trn
from .taskbar import TaskbarProgress, TBPF_ERROR
from .widgets import DropZone, FileRow, Segmented, label, button, human_size

PRESET_NAMES = {
    "youtube_ready": "YouTube Ready",
    "podcast_publisher": "Podcast Publisher",
    "social_media_pack": "Social Media (WebP)",
    "ebook_pack": "eBook (PDF)",
}
PRESET_TOOLTIPS = {
    "youtube_ready": "Videos → YouTube-friendly MP4 (H.264, AAC, fast-start)",
    "podcast_publisher": "Video/audio → extract audio → normalize to -16 LUFS → MP3",
    "social_media_pack": "Images → web-optimized WebP",
    "ebook_pack": "Documents → PDF",
}


# ---------------------------------------------------------------- thumbnails
class _ThumbSignals(QObject):
    ready = pyqtSignal(object, object, object)   # row id, png bytes, duration


class _ThumbJob(QRunnable):
    def __init__(self, row_id, path, fmt, want_duration, signals):
        super().__init__()
        self.row_id, self.path, self.fmt, self.want_duration, self.signals = row_id, path, fmt, want_duration, signals

    def run(self):
        from modules.media import thumbnail, duration
        png = thumbnail(self.path, self.fmt, 96)
        dur = duration(self.path) if self.want_duration else None
        self.signals.ready.emit(self.row_id, png, dur)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(resource('assets', 'icon.ico')))
        self.resize(1080, 700)
        self.setMinimumSize(800, 540)
        self.setAcceptDrops(True)

        self.rows = []             # FileRow widgets, in list order
        self._temp_dirs = []       # extracted ZIPs / pasted images
        self._temp_files = set()   # files without a real home folder (ZIP, clipboard)
        self.worker = None
        self.tasks = []
        self.results = {}
        self.update_info = None
        self._checker = None
        self._taskbar = None
        self._first_show = True
        self._last_outputs = []

        self._thumb_pool = QThreadPool(self)
        self._thumb_pool.setMaxThreadCount(2)
        self._thumb_signals = _ThumbSignals()
        self._thumb_signals.ready.connect(self._thumb_ready)

        self._build()
        self._shortcuts()
        self.refresh_theme()
        self._update_state()

        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        except Exception:
            pass
        if self.config.get("auto_update"):
            QTimer.singleShot(2500, lambda: self.check_for_updates(silent=True))

    # ================================================================ layout
    def _build(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ---- header
        header = QFrame()
        header.setObjectName("Header")
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 12, 14, 12)
        h.setSpacing(10)
        self.logo = QLabel()
        self.logo.setPixmap(QIcon(resource('assets', 'icon.ico')).pixmap(26, 26))
        h.addWidget(self.logo)
        h.addWidget(label(APP_NAME, "title"))
        h.addStretch()
        self.update_btn = button(tr("Update available"), "update")
        self.update_btn.hide()
        self.update_btn.clicked.connect(self.show_update_dialog)
        h.addWidget(self.update_btn)
        self.add_btn = button(tr("Add files"), "ghost", 'plus')
        self.add_btn.clicked.connect(self.add_files_dialog)
        h.addWidget(self.add_btn)
        self.settings_btn = button("", "icon", 'settings', tooltip=tr("Settings (Ctrl+,)"), size=18)
        self.settings_btn.clicked.connect(self.open_settings)
        h.addWidget(self.settings_btn)
        v.addWidget(header)

        # ---- body
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)

        empty = QWidget()
        ev = QVBoxLayout(empty)
        ev.setContentsMargins(28, 24, 28, 24)
        self.drop_zone = DropZone()
        self.drop_zone.clicked.connect(self.add_files_dialog)
        ev.addWidget(self.drop_zone)
        self.stack.addWidget(empty)

        queue = QWidget()
        qv = QVBoxLayout(queue)
        qv.setContentsMargins(20, 16, 20, 4)
        qv.setSpacing(10)
        tb = QHBoxLayout()
        tb.setSpacing(8)
        self.summary = label("", "h2")
        tb.addWidget(self.summary)
        self.summary_sub = label("", "muted")
        tb.addWidget(self.summary_sub)
        tb.addStretch()
        self.combine_btn = button(tr("Combine to PDF"), "ghost", 'layers', tooltip=tr("Combine images and PDFs into one PDF"))
        self.combine_btn.clicked.connect(self.combine_to_pdf)
        tb.addWidget(self.combine_btn)
        self.bulk_label = label(tr("Convert all to"), "muted")
        tb.addWidget(self.bulk_label)
        self.bulk_combo = QComboBox()
        self.bulk_combo.setMinimumWidth(110)
        self.bulk_combo.setToolTip(tr("Set the target format for every file that supports it"))
        self.bulk_combo.activated.connect(self.apply_bulk_format)
        tb.addWidget(self.bulk_combo)
        self.clear_btn = button(tr("Clear"), "ghost", 'trash', tooltip=tr("Remove all files from the list"))
        self.clear_btn.clicked.connect(self.remove_all)
        tb.addWidget(self.clear_btn)
        qv.addLayout(tb)

        self.list = QListWidget()
        self.list.setObjectName("FileList")
        self.list.setSpacing(4)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemSelectionChanged.connect(self._selection_changed)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        qv.addWidget(self.list, 1)
        self.stack.addWidget(queue)

        # ---- bottom bar
        bottom = QFrame()
        bottom.setObjectName("BottomBar")
        bv = QVBoxLayout(bottom)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(0)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.hide()
        bv.addWidget(self.progress)

        b = QHBoxLayout()
        b.setContentsMargins(20, 12, 20, 14)
        b.setSpacing(18)
        b.addLayout(self._field(tr("Save to"), self._make_output_button()))

        self.quality = Segmented([("low", tr("Smaller")), ("medium", tr("Balanced")), ("high", tr("Best"))],
                                 self.config.get("quality") or "medium")
        self.quality.changed.connect(lambda q: self.config.set("quality", q))
        self.quality.setToolTip(tr("Compression for images, video and audio"))
        b.addLayout(self._field(tr("Quality"), self.quality))

        wf = QHBoxLayout()
        wf.setSpacing(4)
        self.workflow = QComboBox()
        self.workflow.setMinimumWidth(190)
        self.workflow.currentIndexChanged.connect(self._workflow_changed)
        wf.addWidget(self.workflow)
        self.builder_btn = button("", "icon", 'layers', tooltip=tr("Build your own workflow"))
        self.builder_btn.clicked.connect(self.open_pipeline_builder)
        wf.addWidget(self.builder_btn)
        b.addLayout(self._field(tr("Workflow"), wf))
        self.load_presets()

        b.addStretch()
        right = QVBoxLayout()
        right.setSpacing(4)
        self.status_line = label("", "subtle")
        self.status_line.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.status_line)
        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.addStretch()
        self.open_out_btn = button(tr("Open folder"), "ghost", 'folder-open')
        self.open_out_btn.clicked.connect(self.open_last_output)
        self.open_out_btn.hide()
        btns.addWidget(self.open_out_btn)
        self.convert_btn = button(tr("Convert"), "primary")
        self.convert_btn.setMinimumWidth(160)
        self.convert_btn.clicked.connect(self.on_convert_clicked)
        btns.addWidget(self.convert_btn)
        right.addLayout(btns)
        b.addLayout(right)
        bv.addLayout(b)
        v.addWidget(bottom)

    def _field(self, title, widget_or_layout):
        col = QVBoxLayout()
        col.setSpacing(5)
        col.addWidget(label(title.upper(), "section"))
        if isinstance(widget_or_layout, QWidget):
            col.addWidget(widget_or_layout)
        else:
            col.addLayout(widget_or_layout)
        return col

    def _make_output_button(self):
        self.out_btn = QToolButton()
        self.out_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.out_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.out_btn.setMaximumWidth(280)
        self.out_btn.setIconSize(QSize(16, 16))
        menu = QMenu(self.out_btn)
        self.act_source = QAction(tr("Same folder as original"), menu, checkable=True)
        self.act_source.triggered.connect(lambda: self._set_output_mode("source"))
        self.act_folder = QAction(tr("Fixed folder"), menu, checkable=True)
        self.act_folder.triggered.connect(lambda: self._set_output_mode("folder"))
        menu.addAction(self.act_source)
        menu.addAction(self.act_folder)
        menu.addSeparator()
        menu.addAction(tr("Choose folder…"), self.choose_output_folder)
        menu.addAction(tr("Open output folder"), self.open_output_folder)
        self.out_btn.setMenu(menu)
        self._refresh_output_button()
        return self.out_btn

    def _shortcuts(self):
        QShortcut(QKeySequence.StandardKey.Open, self, self.add_files_dialog)
        QShortcut(QKeySequence.StandardKey.Paste, self, self.paste)
        QShortcut(QKeySequence("Ctrl+,"), self, self.open_settings)
        QShortcut(QKeySequence("Ctrl+Return"), self, self.on_convert_clicked)
        QShortcut(QKeySequence.StandardKey.Delete, self.list, self.remove_selected)
        QShortcut(QKeySequence.StandardKey.SelectAll, self.list, self.list.selectAll)

    # ================================================================ theme / first start
    def refresh_theme(self):
        c = theme.colors()
        self.add_btn.setIcon(icons.icon('plus', c['muted'], 16))
        self.settings_btn.setIcon(icons.icon('settings', c['muted'], 18))
        self.clear_btn.setIcon(icons.icon('trash', c['muted'], 15))
        self.combine_btn.setIcon(icons.icon('pdf', c['muted'], 15))
        self.builder_btn.setIcon(icons.icon('layers', c['muted'], 17))
        self.open_out_btn.setIcon(icons.icon('folder-open', c['muted'], 16))
        self.out_btn.setIcon(icons.icon('folder', c['muted'], 16))
        self.update_btn.setIcon(icons.icon('download', c['accent'], 14))
        self.drop_zone.refresh_icons()
        for r in self.rows:
            r.refresh_theme()
        theme.set_dark_titlebar(self)

    def _system_theme_changed(self, *_):
        if self.config.get("theme_mode") == "System":
            theme.apply("System")
            self.refresh_theme()

    def showEvent(self, e):
        super().showEvent(e)
        theme.set_dark_titlebar(self)
        if self._first_show:
            self._first_show = False
            self._taskbar = TaskbarProgress(self)
            QTimer.singleShot(250, self._first_start_dialogs)

    def _first_start_dialogs(self):
        from .dialogs import OnboardingDialog, MarkdownDialog
        from modules.changelog import section
        seen = self.config.get("last_seen_version") or ""
        if not self.config.get("onboarded") and not ConfigManager.first_run:
            # Updated from a version without onboarding: show what's new instead
            self.config.set("onboarded", True)
            seen = seen or "0"
        if not self.config.get("onboarded"):
            dlg = OnboardingDialog(self.config, self)
            theme.set_dark_titlebar(dlg)
            dlg.exec()
            self.config.set("onboarded", True)
            theme.apply(self.config.get("theme_mode"))
            self.refresh_theme()
            self._refresh_output_button()
        elif seen and seen != VERSION:
            notes = section(VERSION)
            if notes:
                dlg = MarkdownDialog(tr("What's new in {v}", v=VERSION), "", notes, tr("Got it"), self)
                theme.set_dark_titlebar(dlg)
                dlg.exec()
        self.config.set("last_seen_version", VERSION)

    # ================================================================ output folder
    def _output_mode(self):
        return self.config.get("output_mode") or "source"

    def _refresh_output_button(self):
        mode = self._output_mode()
        self.act_source.setChecked(mode == "source")
        self.act_folder.setChecked(mode == "folder")
        if mode == "source":
            self.out_btn.setText(tr("Same folder as original"))
            self.out_btn.setToolTip(tr("Converted files are saved next to the originals"))
        else:
            folder = self.config.get("default_output_path") or ""
            name = os.path.basename(folder.rstrip("\\/")) or folder
            self.out_btn.setText(name or tr("Choose folder…"))
            self.out_btn.setToolTip(folder)

    def _set_output_mode(self, mode):
        if mode == "folder" and not self.config.get("default_output_path"):
            self.choose_output_folder()
            return
        self.config.set("output_mode", mode)
        self._refresh_output_button()

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Choose output folder"),
                                                  self.config.get("default_output_path") or os.path.expanduser("~"))
        if folder:
            self.config.set("default_output_path", folder)
            self.config.set("output_mode", "folder")
        self._refresh_output_button()

    def _fallback_folder(self):
        folder = self.config.get("default_output_path")
        if not folder or folder == os.path.expanduser("~"):
            folder = os.path.join(os.path.expanduser("~"), "Documents", APP_NAME)
        return folder

    def output_dir_for(self, src):
        if self._output_mode() == "source":
            return self._fallback_folder() if src in self._temp_files else os.path.dirname(src)
        return self.config.get("default_output_path") or self._fallback_folder()

    def open_output_folder(self):
        folder = self.output_dir_for(self.rows[0].path) if self.rows else (
            self._fallback_folder() if self._output_mode() == "source" else self.config.get("default_output_path"))
        if folder and os.path.isdir(folder):
            os.startfile(folder)

    # ================================================================ adding files
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and not self.is_busy():
            e.acceptProposedAction()
            self.drop_zone.set_hover(True)
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls() and not self.is_busy():
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self.drop_zone.set_hover(False)

    def dropEvent(self, e):
        self.drop_zone.set_hover(False)
        self.add_paths([u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()])

    def add_files_dialog(self):
        if self.is_busy():
            return
        files, _ = QFileDialog.getOpenFileNames(self, tr("Add files"), self.config.get("default_open_path") or "")
        if files:
            self.config.set("default_open_path", os.path.dirname(files[0]))
            self.add_paths(files)

    def paste(self):
        """Ctrl+V: files copied in Explorer, or an image (screenshot, browser)."""
        if self.is_busy():
            return
        mime = QApplication.clipboard().mimeData()
        if mime.hasUrls():
            paths = [u.toLocalFile() for u in mime.urls() if u.toLocalFile()]
            if paths:
                self.add_paths(paths)
                return
        if mime.hasImage():
            img = QApplication.clipboard().image()
            if not img.isNull():
                folder = tempfile.mkdtemp(prefix="yprite_paste_")
                self._temp_dirs.append(folder)
                path = os.path.join(folder, f"{tr('Pasted image')} {datetime.now():%Y-%m-%d %H-%M-%S}.png")
                img.save(path, "PNG")
                self._temp_files.add(path)
                self.add_paths([path])
                return
        self.status_line.setText(tr("Nothing to paste — copy files or an image first"))

    def receive_paths(self, paths):
        """Files handed over from Explorer / a second app instance."""
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        self.add_paths(paths)

    @staticmethod
    def _walk(folder):
        out = []
        for root, _dirs, files in os.walk(folder):
            out += [os.path.join(root, f) for f in sorted(files)]
        return out

    def add_paths(self, paths):
        if self.is_busy():
            return
        files = []
        for p in paths:
            if os.path.isdir(p):
                files += self._walk(p)
            elif os.path.isfile(p):
                files.append(p)

        known = {os.path.normcase(os.path.abspath(r.path)) for r in self.rows}
        skipped = 0
        self.list.setUpdatesEnabled(False)
        try:
            for path in files:
                key = os.path.normcase(os.path.abspath(path))
                if key in known:
                    continue
                known.add(key)
                det = detect(path)
                if det.effective == 'zip':
                    self._add_zip(path)
                    continue
                options = target_options(det)
                if not options and len(files) > 1:
                    skipped += 1   # folder adds: quietly skip desktop.ini, thumbs.db, ...
                    continue
                self._add_row(path, det, options)
        finally:
            self.list.setUpdatesEnabled(True)

        if skipped:
            self.status_line.setText(trn("Skipped {n} file that can't be converted",
                                         "Skipped {n} files that can't be converted", skipped))
        self._refresh_bulk()
        self._update_state()

    def _add_row(self, path, det, options):
        row = FileRow(path, det, options)
        row.remove_requested.connect(self._remove_row)
        row.reveal_requested.connect(lambda r: self.reveal(r.output))
        row.details_requested.connect(self._show_error)
        row.options_requested.connect(self.edit_video_options)
        row.combo.currentIndexChanged.connect(lambda *_: self._update_state())
        # Remember the format the user picked last time for this kind of file
        last = (self.config.get("last_targets") or {}).get(det.effective)
        if last:
            row.set_target(last)
        row.combo.activated.connect(lambda _i, r=row: self._remember_target(r))
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 68))
        self.list.addItem(item)
        self.list.setItemWidget(item, row)
        self.rows.append(row)
        if self.workflow.currentData() is not None:
            row.set_busy(False, pipeline_mode=True)
        cat = FormatRules.get_category(det.effective or '')
        if cat in ('image', 'video') or det.effective == 'pdf':
            self._thumb_pool.start(_ThumbJob(id(row), path, det.effective, cat == 'video', self._thumb_signals))

    def _thumb_ready(self, row_id, png, duration):
        for r in self.rows:
            if id(r) == row_id:
                if png:
                    r.set_thumbnail(png)
                if duration:
                    r.duration = duration
                break

    def _remember_target(self, row):
        targets = dict(self.config.get("last_targets") or {})
        targets[row.det.effective] = row.target()
        self.config.set("last_targets", targets)

    def _add_zip(self, path):
        try:
            tmp = tempfile.mkdtemp(prefix="yprite_zip_")
            self._temp_dirs.append(tmp)
            with zipfile.ZipFile(path) as z:
                z.extractall(tmp)
            extracted = self._walk(tmp)
            self._temp_files.update(extracted)
            self.add_paths(extracted)
        except Exception as e:
            QMessageBox.warning(self, "ZIP", tr("Couldn't open {name}:\n{err}", name=os.path.basename(path), err=e))

    # ================================================================ list management
    def _selection_changed(self):
        selected = {self.list.row(i) for i in self.list.selectedItems()}
        for i, r in enumerate(self.rows):
            r.set_selected(i in selected)

    def _selected_rows(self):
        return [self.rows[self.list.row(i)] for i in self.list.selectedItems()]

    def _remove_indices(self, indices):
        for i in sorted(set(indices), reverse=True):
            if 0 <= i < len(self.rows):
                self.list.takeItem(i)
                self.rows.pop(i)
        self._refresh_bulk()
        self._update_state()

    def _remove_row(self, row):
        if not self.is_busy() and row in self.rows:
            self._remove_indices([self.rows.index(row)])

    def remove_selected(self):
        if not self.is_busy():
            self._remove_indices(self.list.row(i) for i in self.list.selectedItems())

    def remove_all(self):
        if self.is_busy():
            return
        self.list.clear()
        self.rows.clear()
        self.status_line.setText("")
        self.open_out_btn.hide()
        self._refresh_bulk()
        self._update_state()

    def remove_with_status(self, status):
        self._remove_indices(i for i, r in enumerate(self.rows) if r.status == status)

    def _context_menu(self, pos):
        item = self.list.itemAt(pos)
        menu = QMenu(self)
        busy = self.is_busy()
        if item:
            row = self.rows[self.list.row(item)]
            menu.addAction(tr("Show original in Explorer"), lambda: self.reveal(row.path))
            if row.output:
                menu.addAction(tr("Show converted file"), lambda: self.reveal(row.output))
            if row.is_video():
                menu.addAction(tr("Video options…"), lambda: self.edit_video_options(row)).setEnabled(not busy)
            if row.det.effective == 'pdf':
                menu.addAction(tr("Split PDF into pages"), lambda: self.split_pdf(row)).setEnabled(not busy)
            menu.addSeparator()
        for text, fn in ((tr("Remove selected"), self.remove_selected),
                         (tr("Remove finished"), lambda: self.remove_with_status("Done")),
                         (tr("Remove all"), self.remove_all)):
            menu.addAction(text, fn).setEnabled(not busy)
        menu.exec(self.list.viewport().mapToGlobal(pos))

    @staticmethod
    def reveal(path):
        if path and os.path.exists(path):
            subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])

    def _show_error(self, row):
        box = QMessageBox(self)
        box.setWindowTitle(tr("Conversion failed"))
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(tr("<b>{name}</b> couldn't be converted.", name=os.path.basename(row.path)))
        box.setInformativeText(row.message or tr("Unknown error"))
        box.exec()

    def _refresh_bulk(self):
        seen = []
        for r in self.rows:
            for fmt, text in r.options:
                if fmt not in seen and "·" not in text:
                    seen.append(fmt)
        self.bulk_combo.blockSignals(True)
        self.bulk_combo.clear()
        self.bulk_combo.addItem(tr("Choose…"), None)
        for f in seen:
            self.bulk_combo.addItem(f, f)
        self.bulk_combo.blockSignals(False)

    def apply_bulk_format(self, _i):
        fmt = self.bulk_combo.currentData()
        if fmt:
            for r in self.rows:
                r.set_target(fmt)
        self.bulk_combo.setCurrentIndex(0)

    # ================================================================ video / pdf tools
    def edit_video_options(self, row):
        from .dialogs import VideoOptionsDialog
        if row.duration is None:
            from modules.media import duration
            row.duration = duration(row.path)
        dlg = VideoOptionsDialog(row, self)
        theme.set_dark_titlebar(dlg)
        if dlg.exec() and dlg.result_opts is not None:
            from converters.video_converter import options_active
            opts = dlg.result_opts if options_active(dlg.result_opts) else None
            targets = [r for r in self.rows if r.is_video()] if dlg.apply_all.isChecked() else [row]
            for r in targets:
                r.video_opts = dict(opts) if opts else None
                r.refresh_details()
                r.refresh_theme()

    def _pdf_candidates(self):
        def ok(r):
            cat = FormatRules.get_category(r.det.effective or '')
            return cat == 'image' or r.det.effective == 'pdf'
        selected = [r for r in self._selected_rows() if ok(r)]
        return selected if len(selected) >= 2 else [r for r in self.rows if ok(r)]

    def combine_to_pdf(self):
        from .dialogs import CombinePdfDialog
        rows = self._pdf_candidates()
        if not rows:
            return
        dlg = CombinePdfDialog([r.path for r in rows], self.output_dir_for(rows[0].path),
                               self.quality.value() or "medium", self)
        theme.set_dark_titlebar(dlg)
        if dlg.exec() and dlg.created:
            self._last_outputs = [dlg.created]
            self.open_out_btn.show()
            self.status_line.setText(tr("Created {name}", name=os.path.basename(dlg.created)))

    def split_pdf(self, row):
        from .dialogs import FuncThread
        from modules.pdf_tools import split
        folder = self.output_dir_for(row.path)
        row.set_status("Running")
        self._split_thread = FuncThread(split, row.path, folder)

        def done(files):
            row.output = files[0] if files else None
            row.set_status("Done", tr("Split into {n} pages", n=len(files)))
            self._last_outputs = files
            self.open_out_btn.show()
            self.status_line.setText(tr("Split into {n} pages", n=len(files)))

        def failed(err):
            row.set_status("Error", tr("Couldn't split the PDF:\n{err}", err=err))

        self._split_thread.done.connect(done)
        self._split_thread.failed.connect(failed)
        self._split_thread.start()

    # ================================================================ state
    def is_busy(self):
        return self.worker is not None and self.worker.isRunning()

    def _convertible_rows(self):
        if self.workflow.currentData() is not None:
            return [r for r in self.rows if r.det.effective]
        return [r for r in self.rows if r.target()]

    def _update_state(self):
        self.stack.setCurrentIndex(1 if self.rows else 0)
        n = len(self.rows)
        self.summary.setText(trn("{n} file", "{n} files", n))
        self.summary_sub.setText(human_size(sum(r.size for r in self.rows)) if n else "")
        self.combine_btn.setVisible(len(self._pdf_candidates()) >= 2)
        if self.is_busy():
            return
        todo = len(self._convertible_rows())
        self.convert_btn.setEnabled(todo > 0)
        self.convert_btn.setText(trn("Convert {n} file", "Convert {n} files", todo) if todo else tr("Convert"))
        pipeline = self.workflow.currentData() is not None
        self.bulk_label.setVisible(not pipeline)
        self.bulk_combo.setVisible(not pipeline)

    # ================================================================ workflows
    def load_presets(self):
        from modules.pipeline_serializer import PresetLibrary
        current = self.workflow.currentData()
        self.workflow.blockSignals(True)
        self.workflow.clear()
        self.workflow.addItem(tr("Simple conversion"), None)
        self.workflow.setItemData(0, tr("Convert each file to the format chosen in its row"), Qt.ItemDataRole.ToolTipRole)
        for p in PresetLibrary().list_presets():
            key = p['filename'][:-5]
            self.workflow.addItem(PRESET_NAMES.get(key, p['name']), key)
            self.workflow.setItemData(self.workflow.count() - 1, PRESET_TOOLTIPS.get(key, p['description']),
                                      Qt.ItemDataRole.ToolTipRole)
        idx = self.workflow.findData(current)
        self.workflow.setCurrentIndex(max(idx, 0))
        self.workflow.blockSignals(False)

    def _workflow_changed(self, _i):
        pipeline = self.workflow.currentData() is not None
        for r in self.rows:
            r.set_busy(False, pipeline_mode=pipeline)
        self._update_state()

    def open_pipeline_builder(self):
        from ui.pipeline_builder import PipelineBuilderDialog
        dlg = PipelineBuilderDialog(self)
        theme.set_dark_titlebar(dlg)
        if dlg.exec():
            self.load_presets()

    # ================================================================ conversion
    def on_convert_clicked(self):
        if self.is_busy():
            self.worker.stop()
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText(tr("Stopping…"))
            return
        if self.convert_btn.isEnabled():
            self.start_conversion()

    @staticmethod
    def _unique_dest(folder, base, ext, reserved):
        candidate = os.path.join(folder, f"{base}.{ext}")
        n = 1
        while os.path.exists(candidate) or os.path.normcase(candidate) in reserved:
            candidate = os.path.join(folder, f"{base} ({n}).{ext}")
            n += 1
        reserved.add(os.path.normcase(candidate))
        return candidate

    def start_conversion(self):
        preset_key = self.workflow.currentData()
        pipeline = None
        if preset_key is not None:
            from modules.pipeline_serializer import PresetLibrary
            pipeline = PresetLibrary().get_preset(preset_key)
            if pipeline is None:
                QMessageBox.critical(self, tr("Workflow"), tr("This workflow could not be loaded."))
                return
            ok, msg = pipeline.validate()
            if not ok:
                QMessageBox.warning(self, tr("Workflow"), msg)
                return

        quality = self.quality.value() or "medium"
        tasks, reserved = [], set()
        for r in self._convertible_rows():
            folder = self.output_dir_for(r.path)
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self, tr("Output folder"), tr("Can't write to {folder}:\n{err}", folder=folder, err=e))
                return
            base = os.path.splitext(os.path.basename(r.path))[0]
            if pipeline:
                dest = self._unique_dest(folder, f"{base}_converted", r.det.effective or 'out', reserved)
                tasks.append({'index': id(r), 'source': r.path, 'dest': dest})
            else:
                fmt = r.target()
                if fmt == r.det.effective and not r.det.mismatch:
                    base += "_edit"   # same format (rotate/trim/shrink): never look like the original
                task = {'index': id(r), 'source': r.path, 'format': fmt, 'quality': quality,
                        'dest': self._unique_dest(folder, base, fmt, reserved)}
                if r.video_opts and r.is_video():
                    task['video_options'] = r.video_opts
                tasks.append(task)
            r.output = None
            r.set_status("Queued")

        if not tasks:
            return
        if pipeline:
            from modules.pipeline_worker import PipelineWorker
            self.worker = PipelineWorker(tasks, pipeline)
        else:
            self.worker = ConversionWorker(tasks)
        self.tasks = tasks
        self._task_by_id = {t['index']: t for t in tasks}
        self._row_by_id = {id(r): r for r in self.rows}
        self.results = {"Done": 0, "Error": 0, "Cancelled": 0}

        self.progress.setRange(0, len(tasks))
        self.progress.setValue(0)
        self.progress.show()
        if self._taskbar:
            self._taskbar.set_value(0, len(tasks))
        self.open_out_btn.hide()
        self.convert_btn.setText(tr("Cancel"))
        self.convert_btn.setProperty("kind", "danger")
        theme.repolish(self.convert_btn)
        self._set_controls_enabled(False)

        self.worker.progress.connect(self._on_progress)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _set_controls_enabled(self, on):
        for w in (self.add_btn, self.clear_btn, self.bulk_combo, self.workflow, self.quality,
                  self.out_btn, self.builder_btn, self.combine_btn):
            w.setEnabled(on)
        pipeline = self.workflow.currentData() is not None
        for r in self.rows:
            r.set_busy(not on, pipeline_mode=pipeline)

    def _on_progress(self, file_id, status, message):
        row = self._row_by_id.get(file_id)
        if row is None:
            return
        if status == "Done":
            row.output = self._task_by_id[file_id]['dest']
        row.set_status(status, message)
        if status == "Running":
            done = sum(self.results.values())
            self.status_line.setText(tr("{done} of {total}  ·  {name}", done=done + 1, total=len(self.tasks),
                                        name=os.path.basename(row.path)))
        if status in self.results:
            self.results[status] += 1
            done = sum(self.results.values())
            self.progress.setValue(done)
            if self._taskbar:
                self._taskbar.set_value(done, len(self.tasks))

    def _on_finished(self):
        self.worker = None
        self.progress.hide()
        self.convert_btn.setProperty("kind", "primary")
        theme.repolish(self.convert_btn)
        self._set_controls_enabled(True)

        done, err, cancelled = self.results["Done"], self.results["Error"], self.results["Cancelled"]
        parts = [tr("{n} converted", n=done)]
        if err:
            parts.append(tr("{n} failed", n=err))
        if cancelled:
            parts.append(tr("{n} cancelled", n=cancelled))
        before = sum(r.size for r in self.rows if r.output and r.status == "Done")
        after = 0
        for r in self.rows:
            if r.output and r.status == "Done":
                try:
                    after += os.path.getsize(r.output)
                except OSError:
                    pass
        if done and after < before:
            parts.append(tr("saved {size}", size=human_size(before - after)))
        self.status_line.setText("  ·  ".join(parts))
        self._last_outputs = [r.output for r in self.rows if r.output]
        self.open_out_btn.setVisible(bool(self._last_outputs))

        if self._taskbar:
            if err:
                self._taskbar.set_state(TBPF_ERROR)
                QTimer.singleShot(4000, self._taskbar.clear)
            else:
                self._taskbar.clear()

        if self.config.get("auto_remove_finished"):
            self.remove_with_status("Done")
        self._update_state()

        if not self.isActiveWindow():
            QApplication.alert(self)
        if done and self.config.get("open_folder_when_done"):
            self.open_last_output()

    def open_last_output(self):
        if self._last_outputs:
            self.reveal(self._last_outputs[0])

    # ================================================================ settings / updates
    def open_settings(self):
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        theme.set_dark_titlebar(dlg)
        if dlg.exec():
            theme.apply(self.config.get("theme_mode"))
            self.refresh_theme()
            self._refresh_output_button()
            for r in self.rows:  # advanced formats may have changed
                r.set_options(target_options(r.det))
            self._refresh_bulk()
            self._update_state()

    def check_for_updates(self, silent=True, on_done=None):
        from modules.updater import UpdateChecker
        if self._checker and self._checker.isRunning():
            return
        self._checker = UpdateChecker()

        def got(info):
            if info and (not silent or info.version != self.config.get("skipped_version")):
                self.update_info = info
                self.update_btn.setText(tr("Update {v}", v=info.version))
                self.update_btn.show()
            if on_done:
                on_done(info, None)

        def failed(err):
            if on_done:
                on_done(None, err)

        self._checker.result.connect(got)
        self._checker.failed.connect(failed)
        self._checker.start()

    def show_update_dialog(self):
        if not self.update_info:
            return
        from .update_dialog import UpdateDialog
        dlg = UpdateDialog(self.update_info, self)
        theme.set_dark_titlebar(dlg)
        result = dlg.exec()
        if dlg.skipped:
            self.config.set("skipped_version", self.update_info.version)
            self.update_btn.hide()
        elif result and dlg.installer_started:
            self._quit_for_update = True
            self.close()

    def closeEvent(self, e):
        if self.is_busy() and not getattr(self, '_quit_for_update', False):
            if QMessageBox.question(self, tr("Conversion running"),
                                    tr("A conversion is still running. Stop it and quit?")) != QMessageBox.StandardButton.Yes:
                e.ignore()
                return
        if self.worker:
            self.worker.stop()
            self.worker.wait(5000)
        self._thumb_pool.clear()
        self._thumb_pool.waitForDone(2000)
        for d in self._temp_dirs:
            shutil.rmtree(d, ignore_errors=True)
        super().closeEvent(e)
        QApplication.quit()
