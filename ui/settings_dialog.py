import os
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QLineEdit, QFileDialog,
                             QScrollArea, QWidget, QFrame, QGridLayout)

from app_info import APP_NAME, VERSION, GITHUB_URL
from modules.config_manager import ConfigManager
from converters.base_converter import tool_available as tool_status
from . import theme, icons
from .widgets import label, button, Segmented


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = ConfigManager()
        self.main = parent
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 640)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("Root")
        v = QVBoxLayout(body)
        v.setContentsMargins(28, 24, 28, 16)
        v.setSpacing(10)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        v.addWidget(label("Settings", "h1"))
        v.addSpacing(6)

        # ---------- appearance
        v.addWidget(label("APPEARANCE", "section"))
        card, c = self._card()
        row = QHBoxLayout()
        row.addWidget(label("Theme"))
        row.addStretch()
        self.theme_seg = Segmented([("System", "System"), ("Light", "Light"), ("Dark", "Dark")],
                                   self.cfg.get("theme_mode"))
        row.addWidget(self.theme_seg)
        c.addLayout(row)
        v.addWidget(card)

        # ---------- behaviour
        v.addSpacing(8)
        v.addWidget(label("CONVERSION", "section"))
        card, c = self._card()
        self.open_done = self._check(c, "Open the output folder when a batch is finished", "open_folder_when_done")
        self.auto_remove = self._check(c, "Remove finished files from the list", "auto_remove_finished")
        self.advanced = self._check(c, "Show advanced formats (AVI, MOV, WMA, Opus, …)", "enable_advanced_formats")
        v.addWidget(card)

        # ---------- updates
        v.addSpacing(8)
        v.addWidget(label("UPDATES", "section"))
        card, c = self._card()
        self.auto_update = self._check(c, "Check for updates automatically", "auto_update")
        row = QHBoxLayout()
        self.update_state = label(f"You're on version {VERSION}", "muted")
        row.addWidget(self.update_state)
        row.addStretch()
        self.check_btn = button("Check now", None, 'refresh')
        self.check_btn.clicked.connect(self._check_updates)
        row.addWidget(self.check_btn)
        c.addLayout(row)
        v.addWidget(card)

        # ---------- tools
        v.addSpacing(8)
        v.addWidget(label("CONVERSION ENGINES", "section"))
        card, c = self._card()
        hint = label("FFmpeg ships with the app. LibreOffice, Pandoc and ImageMagick are optional — "
                     "install them to unlock more document formats.", "subtle")
        hint.setWordWrap(True)
        c.addWidget(hint)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.paths = {}
        tools = [("FFmpeg", "ffmpeg_path", "Video & audio"),
                 ("LibreOffice", "soffice_path", "Office → PDF"),
                 ("Pandoc", "pandoc_path", "Docs ↔ Markdown/HTML"),
                 ("ImageMagick", "magick_path", "Rare image formats")]
        for r, (name, key, purpose) in enumerate(tools):
            ok = tool_status(self.cfg.get(key))
            dot = label("●" if ok else "○")
            dot.setStyleSheet(f"color: {theme.colors()['success' if ok else 'subtle']};")
            dot.setToolTip("Found" if ok else "Not found")
            grid.addWidget(dot, r, 0)
            name_lbl = label(name)
            name_lbl.setToolTip(purpose)
            grid.addWidget(name_lbl, r, 1)
            edit = QLineEdit(str(self.cfg.get(key) or ""))
            edit.setPlaceholderText(purpose)
            self.paths[key] = edit
            grid.addWidget(edit, r, 2)
            browse = button("", "icon", 'folder', tooltip="Browse…")
            browse.clicked.connect(lambda _=False, e=edit: self._browse(e))
            grid.addWidget(browse, r, 3)
        grid.setColumnStretch(2, 1)
        c.addLayout(grid)
        v.addWidget(card)

        # ---------- about
        v.addSpacing(8)
        v.addWidget(label("ABOUT", "section"))
        card, c = self._card()
        row = QHBoxLayout()
        row.addWidget(label(f"{APP_NAME} {VERSION}"))
        row.addStretch()
        gh = button("GitHub", "ghost", 'github')
        gh.clicked.connect(lambda: webbrowser.open(GITHUB_URL))
        row.addWidget(gh)
        data = button("Data folder", "ghost", 'folder-open')
        data.clicked.connect(self._open_data_folder)
        row.addWidget(data)
        c.addLayout(row)
        v.addWidget(card)
        v.addStretch()

        # ---------- footer
        footer = QFrame()
        footer.setObjectName("BottomBar")
        f = QHBoxLayout(footer)
        f.setContentsMargins(20, 12, 20, 12)
        f.addStretch()
        cancel = button("Cancel")
        cancel.clicked.connect(self.reject)
        f.addWidget(cancel)
        save = button("Save", "primary")
        save.clicked.connect(self.save)
        save.setDefault(True)
        f.addWidget(save)
        outer.addWidget(footer)

    def _card(self):
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        return card, lay

    def _check(self, layout, text, key):
        cb = QCheckBox(text)
        cb.setChecked(bool(self.cfg.get(key)))
        cb.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(cb)
        return cb

    def _browse(self, edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select program", os.path.dirname(edit.text()) or "",
                                              "Programs (*.exe);;All files (*)")
        if path:
            edit.setText(path)

    def _open_data_folder(self):
        from modules.paths import user_dir
        os.startfile(user_dir())

    def _check_updates(self):
        if not self.main:
            return
        self.check_btn.setEnabled(False)
        self.update_state.setText("Checking…")

        def done(info, err):
            self.check_btn.setEnabled(True)
            if err:
                self.update_state.setText("Couldn't reach GitHub")
                self.update_state.setToolTip(err)
            elif info:
                self.update_state.setText(f"Version {info.version} is available")
                self.reject()
                self.main.show_update_dialog()
            else:
                self.update_state.setText(f"You're up to date ({VERSION})")

        self.main.check_for_updates(silent=False, on_done=done)

    def save(self):
        for key, edit in self.paths.items():
            self.cfg.set(key, edit.text().strip())
        self.cfg.set("theme_mode", self.theme_seg.value())
        self.cfg.set("open_folder_when_done", self.open_done.isChecked())
        self.cfg.set("auto_remove_finished", self.auto_remove.isChecked())
        self.cfg.set("enable_advanced_formats", self.advanced.isChecked())
        self.cfg.set("auto_update", self.auto_update.isChecked())
        self.accept()
