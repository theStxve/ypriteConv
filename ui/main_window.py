import os
import shutil
import subprocess
import tempfile
import zipfile

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QIcon, QGuiApplication
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QFileDialog, QMessageBox, QStackedWidget, QListWidget, QListWidgetItem,
                             QProgressBar, QToolButton, QMenu, QApplication, QAbstractItemView, QFrame)

from app_info import APP_NAME, VERSION
from modules.config_manager import ConfigManager
from modules.file_detect import detect, target_options
from modules.paths import resource
from modules.worker import ConversionWorker
from . import icons, theme
from .widgets import DropZone, FileRow, Segmented, ElidedLabel, label, button

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
QUALITY_OPTIONS = [("low", "Smaller"), ("medium", "Balanced"), ("high", "Best")]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(resource('assets', 'icon.ico')))
        self.resize(1040, 680)
        self.setMinimumSize(760, 520)
        self.setAcceptDrops(True)

        self.rows = []             # FileRow widgets, in list order
        self._temp_dirs = []       # extracted ZIPs
        self._temp_files = set()   # files that came from ZIPs (can't save "next to source")
        self.worker = None
        self.tasks = []
        self.results = {}
        self.update_info = None
        self._checker = None

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
        self.update_btn = button("Update available", "update")
        self.update_btn.hide()
        self.update_btn.clicked.connect(self.show_update_dialog)
        h.addWidget(self.update_btn)
        self.add_btn = button("Add files", "ghost", 'plus')
        self.add_btn.clicked.connect(self.add_files_dialog)
        h.addWidget(self.add_btn)
        self.settings_btn = button("", "icon", 'settings', tooltip="Settings (Ctrl+,)", size=18)
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
        self.bulk_label = label("Convert all to", "muted")
        tb.addWidget(self.bulk_label)
        self.bulk_combo = QComboBox()
        self.bulk_combo.setMinimumWidth(110)
        self.bulk_combo.setToolTip("Set the target format for every file that supports it")
        self.bulk_combo.activated.connect(self.apply_bulk_format)
        tb.addWidget(self.bulk_combo)
        self.clear_btn = button("Clear", "ghost", 'trash', tooltip="Remove all files from the list")
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

        b.addLayout(self._field("Save to", self._make_output_button()))

        self.quality = Segmented(QUALITY_OPTIONS, self.config.get("quality") or "medium")
        self.quality.changed.connect(lambda q: self.config.set("quality", q))
        self.quality.setToolTip("Compression for images, video and audio")
        b.addLayout(self._field("Quality", self.quality))

        wf = QHBoxLayout()
        wf.setSpacing(4)
        self.workflow = QComboBox()
        self.workflow.setMinimumWidth(190)
        self.workflow.currentIndexChanged.connect(self._workflow_changed)
        wf.addWidget(self.workflow)
        self.builder_btn = button("", "icon", 'layers', tooltip="Build your own workflow")
        self.builder_btn.clicked.connect(self.open_pipeline_builder)
        wf.addWidget(self.builder_btn)
        b.addLayout(self._field("Workflow", wf))
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
        self.open_out_btn = button("Open folder", "ghost", 'folder-open')
        self.open_out_btn.clicked.connect(self.open_last_output)
        self.open_out_btn.hide()
        btns.addWidget(self.open_out_btn)
        self.convert_btn = button("Convert", "primary")
        self.convert_btn.setMinimumWidth(150)
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
        self.act_source = QAction("Same folder as original", menu, checkable=True)
        self.act_source.triggered.connect(lambda: self._set_output_mode("source"))
        self.act_folder = QAction("Fixed folder", menu, checkable=True)
        self.act_folder.triggered.connect(lambda: self._set_output_mode("folder"))
        menu.addAction(self.act_source)
        menu.addAction(self.act_folder)
        menu.addSeparator()
        menu.addAction("Choose folder…", self.choose_output_folder)
        menu.addAction("Open output folder", self.open_output_folder)
        self.out_btn.setMenu(menu)
        self._refresh_output_button()
        return self.out_btn

    def _shortcuts(self):
        QShortcut(QKeySequence.StandardKey.Open, self, self.add_files_dialog)
        QShortcut(QKeySequence("Ctrl+,"), self, self.open_settings)
        QShortcut(QKeySequence("Ctrl+Return"), self, self.on_convert_clicked)
        QShortcut(QKeySequence.StandardKey.Delete, self.list, self.remove_selected)
        QShortcut(QKeySequence.StandardKey.SelectAll, self.list, self.list.selectAll)

    # ================================================================ theme
    def refresh_theme(self):
        c = theme.colors()
        self.add_btn.setIcon(icons.icon('plus', c['muted'], 16))
        self.settings_btn.setIcon(icons.icon('settings', c['muted'], 18))
        self.clear_btn.setIcon(icons.icon('trash', c['muted'], 15))
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

    # ================================================================ output folder
    def _output_mode(self):
        return self.config.get("output_mode") or "source"

    def _refresh_output_button(self):
        mode = self._output_mode()
        self.act_source.setChecked(mode == "source")
        self.act_folder.setChecked(mode == "folder")
        if mode == "source":
            self.out_btn.setText("Same folder as original")
            self.out_btn.setToolTip("Converted files are saved next to the originals")
        else:
            folder = self.config.get("default_output_path") or ""
            name = os.path.basename(folder.rstrip("\\/")) or folder
            self.out_btn.setText(name or "Choose folder…")
            self.out_btn.setToolTip(folder)

    def _set_output_mode(self, mode):
        if mode == "folder" and not self.config.get("default_output_path"):
            self.choose_output_folder()
            return
        self.config.set("output_mode", mode)
        self._refresh_output_button()

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder",
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
        if self._output_mode() == "source" and src not in self._temp_files:
            return os.path.dirname(src)
        return self._fallback_folder() if self._output_mode() == "source" else self.config.get("default_output_path")

    def open_output_folder(self):
        folder = self._fallback_folder() if self._output_mode() == "source" else self.config.get("default_output_path")
        if self._output_mode() == "source" and self.rows:
            folder = os.path.dirname(self.rows[0].path)
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
        files, _ = QFileDialog.getOpenFileNames(self, "Add files", self.config.get("default_open_path") or "")
        if files:
            self.config.set("default_open_path", os.path.dirname(files[0]))
            self.add_paths(files)

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
                if det.effective == 'zip' or (det.ext == 'zip' and not det.real):
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
            self.status_line.setText(f"Skipped {skipped} file{'s' if skipped != 1 else ''} that can't be converted")
        self._refresh_bulk()
        self._update_state()

    def _add_row(self, path, det, options):
        row = FileRow(path, det, options)
        row.remove_requested.connect(self._remove_row)
        row.reveal_requested.connect(lambda r: self.reveal(r.output))
        row.details_requested.connect(self._show_error)
        row.combo.currentIndexChanged.connect(lambda *_: self._update_state())
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 68))
        self.list.addItem(item)
        self.list.setItemWidget(item, row)
        self.rows.append(row)
        if self.workflow.currentData() is not None:
            row.set_busy(False, pipeline_mode=True)

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
            QMessageBox.warning(self, "ZIP", f"Couldn't open {os.path.basename(path)}:\n{e}")

    # ================================================================ list management
    def _selection_changed(self):
        selected = {self.list.row(i) for i in self.list.selectedItems()}
        for i, r in enumerate(self.rows):
            r.set_selected(i in selected)

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
        if item:
            row = self.rows[self.list.row(item)]
            menu.addAction("Show original in Explorer", lambda: self.reveal(row.path))
            if row.output:
                menu.addAction("Show converted file", lambda: self.reveal(row.output))
            menu.addSeparator()
        busy = self.is_busy()
        for text, fn in (("Remove selected", self.remove_selected),
                         ("Remove finished", lambda: self.remove_with_status("Done")),
                         ("Remove all", self.remove_all)):
            a = menu.addAction(text, fn)
            a.setEnabled(not busy)
        menu.exec(self.list.viewport().mapToGlobal(pos))

    @staticmethod
    def reveal(path):
        if path and os.path.exists(path):
            subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])

    def _show_error(self, row):
        box = QMessageBox(self)
        box.setWindowTitle("Conversion failed")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(f"<b>{os.path.basename(row.path)}</b> couldn't be converted.")
        box.setInformativeText(row.message or "Unknown error")
        box.exec()

    def _refresh_bulk(self):
        seen = []
        for r in self.rows:
            for fmt, _ in r.options:
                if fmt not in seen:
                    seen.append(fmt)
        self.bulk_combo.blockSignals(True)
        self.bulk_combo.clear()
        self.bulk_combo.addItem("Choose…", None)
        for f in seen:
            self.bulk_combo.addItem(f, f)
        self.bulk_combo.blockSignals(False)

    def apply_bulk_format(self, _i):
        fmt = self.bulk_combo.currentData()
        if fmt:
            for r in self.rows:
                r.set_target(fmt)
        self.bulk_combo.setCurrentIndex(0)

    # ================================================================ state
    def is_busy(self):
        return self.worker is not None and self.worker.isRunning()

    def _convertible_rows(self):
        if self.workflow.currentData() is not None:
            return [r for r in self.rows if r.status != "Unsupported" or r.det.effective]
        return [r for r in self.rows if r.target()]

    def _update_state(self):
        self.stack.setCurrentIndex(1 if self.rows else 0)
        n = len(self.rows)
        total = 0
        for r in self.rows:
            try:
                total += os.path.getsize(r.path)
            except OSError:
                pass
        from .widgets import human_size
        self.summary.setText(f"{n} file{'s' if n != 1 else ''}")
        self.summary_sub.setText(human_size(total) if n else "")
        if self.is_busy():
            return
        todo = len(self._convertible_rows())
        self.convert_btn.setEnabled(todo > 0)
        self.convert_btn.setText(f"Convert {todo} file{'s' if todo != 1 else ''}" if todo else "Convert")
        pipeline = self.workflow.currentData() is not None
        self.bulk_label.setVisible(not pipeline)
        self.bulk_combo.setVisible(not pipeline)

    # ================================================================ workflows
    def load_presets(self):
        from modules.pipeline_serializer import PresetLibrary
        current = self.workflow.currentData()
        self.workflow.blockSignals(True)
        self.workflow.clear()
        self.workflow.addItem("Simple conversion", None)
        self.workflow.setItemData(0, "Convert each file to the format chosen in its row", Qt.ItemDataRole.ToolTipRole)
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
            self.convert_btn.setText("Stopping…")
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
                QMessageBox.critical(self, "Workflow", "This workflow could not be loaded.")
                return
            ok, msg = pipeline.validate()
            if not ok:
                QMessageBox.warning(self, "Workflow", msg)
                return

        quality = self.quality.value() or "medium"
        tasks, reserved = [], set()
        for r in self._convertible_rows():
            folder = self.output_dir_for(r.path)
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self, "Output folder", f"Can't write to {folder}:\n{e}")
                return
            base = os.path.splitext(os.path.basename(r.path))[0]
            if pipeline:
                ext = r.det.effective or 'out'
                dest = self._unique_dest(folder, f"{base}_converted", ext, reserved)
                tasks.append({'index': id(r), 'source': r.path, 'dest': dest})
            else:
                fmt = r.target()
                tasks.append({'index': id(r), 'source': r.path, 'format': fmt, 'quality': quality,
                              'dest': self._unique_dest(folder, base, fmt, reserved)})
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
        self.open_out_btn.hide()
        self.convert_btn.setText("Cancel")
        self.convert_btn.setProperty("kind", "danger")
        theme.repolish(self.convert_btn)
        for w in (self.add_btn, self.clear_btn, self.bulk_combo, self.workflow, self.quality,
                  self.out_btn, self.builder_btn):
            w.setEnabled(False)
        for r in self.rows:
            r.set_busy(True)

        self.worker.progress.connect(self._on_progress)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, file_id, status, message):
        row = self._row_by_id.get(file_id)
        if row is None:
            return
        if status == "Done":
            row.output = self._task_by_id[file_id]['dest']
        row.set_status(status, message)
        if status == "Running":
            done = sum(self.results.values())
            self.status_line.setText(f"{done + 1} of {len(self.tasks)}  ·  {os.path.basename(row.path)}")
            self.list.scrollToItem(self.list.item(self.rows.index(row)))
        if status in self.results:
            self.results[status] += 1
            self.progress.setValue(sum(self.results.values()))

    def _on_finished(self):
        self.worker = None
        self.progress.hide()
        self.convert_btn.setProperty("kind", "primary")
        theme.repolish(self.convert_btn)
        for w in (self.add_btn, self.clear_btn, self.bulk_combo, self.workflow, self.quality,
                  self.out_btn, self.builder_btn):
            w.setEnabled(True)
        pipeline = self.workflow.currentData() is not None
        for r in self.rows:
            r.set_busy(False, pipeline_mode=pipeline)

        done, err, cancelled = self.results["Done"], self.results["Error"], self.results["Cancelled"]
        parts = [f"{done} converted"]
        if err:
            parts.append(f"{err} failed")
        if cancelled:
            parts.append(f"{cancelled} cancelled")
        self.status_line.setText("  ·  ".join(parts))
        self._last_outputs = [r.output for r in self.rows if r.output]
        self.open_out_btn.setVisible(bool(self._last_outputs))

        if self.config.get("auto_remove_finished"):
            self.remove_with_status("Done")
        self._update_state()

        if not self.isActiveWindow():
            QApplication.alert(self)
        if done and self.config.get("open_folder_when_done"):
            self.open_last_output()

    def open_last_output(self):
        outs = getattr(self, '_last_outputs', [])
        if outs:
            self.reveal(outs[0])

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
                current = r.target()
                r.options = target_options(r.det)
                r.combo.blockSignals(True)
                r.combo.clear()
                for fmt, text in r.options:
                    r.combo.addItem(text, fmt)
                r.combo.blockSignals(False)
                if current:
                    r.set_target(current)
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
                self.update_btn.setText(f"Update {info.version}")
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
            if QMessageBox.question(self, "Conversion running",
                                    "A conversion is still running. Stop it and quit?") != QMessageBox.StandardButton.Yes:
                e.ignore()
                return
        if self.worker:
            self.worker.stop()
            self.worker.wait(5000)
        for d in self._temp_dirs:
            shutil.rmtree(d, ignore_errors=True)
        super().closeEvent(e)
        QApplication.quit()
