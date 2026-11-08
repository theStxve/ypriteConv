import os
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QLineEdit, QFileDialog,
                             QScrollArea, QWidget, QFrame, QGridLayout, QComboBox)

from app_info import APP_NAME, VERSION, GITHUB_URL
from converters.base_converter import tool_available
from modules.config_manager import ConfigManager
from modules import shell_integration
from . import theme
from .i18n import tr
from .widgets import label, button, Segmented


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = ConfigManager()
        self.main = parent
        self.setWindowTitle(tr("Settings"))
        self.setMinimumSize(620, 680)

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

        v.addWidget(label(tr("Settings"), "h1"))
        v.addSpacing(6)

        # ---------- appearance
        v.addWidget(label(tr("APPEARANCE"), "section"))
        card, c = self._card()
        row = QHBoxLayout()
        row.addWidget(label(tr("Theme")))
        row.addStretch()
        self.theme_seg = Segmented([("System", tr("System")), ("Light", tr("Light")), ("Dark", tr("Dark"))],
                                   self.cfg.get("theme_mode"))
        row.addWidget(self.theme_seg)
        c.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(label(tr("Language")))
        row.addStretch()
        self.lang = QComboBox()
        for value, text in (("System", tr("System")), ("en", "English"), ("de", "Deutsch")):
            self.lang.addItem(text, value)
        self.lang.setCurrentIndex(max(0, self.lang.findData(self.cfg.get("language") or "System")))
        row.addWidget(self.lang)
        c.addLayout(row)
        self.lang_hint = label(tr("Language changes apply after a restart."), "subtle")
        self.lang_hint.hide()
        self.lang.currentIndexChanged.connect(lambda _: self.lang_hint.show())
        c.addWidget(self.lang_hint)
        v.addWidget(card)

        # ---------- behaviour
        v.addSpacing(8)
        v.addWidget(label(tr("CONVERSION"), "section"))
        card, c = self._card()
        self.open_done = self._check(c, tr("Open the output folder when a batch is finished"), "open_folder_when_done")
        self.auto_remove = self._check(c, tr("Remove finished files from the list"), "auto_remove_finished")
        self.advanced = self._check(c, tr("Show advanced formats (AVI, MOV, WMA, Opus, …)"), "enable_advanced_formats")
        v.addWidget(card)

        # ---------- windows integration
        v.addSpacing(8)
        v.addWidget(label(tr("WINDOWS"), "section"))
        card, c = self._card()
        self.ctx = QCheckBox(tr("Show “Convert with ypriteConvert” in the Explorer right-click menu"))
        self.ctx.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ctx.setChecked(shell_integration.is_enabled())
        self.ctx.setEnabled(shell_integration.available())
        if not shell_integration.available():
            self.ctx.setToolTip(tr("Only available in the installed app"))
        c.addWidget(self.ctx)
        v.addWidget(card)

        # ---------- updates
        v.addSpacing(8)
        v.addWidget(label(tr("UPDATES"), "section"))
        card, c = self._card()
        self.auto_update = self._check(c, tr("Check for updates automatically"), "auto_update")
        row = QHBoxLayout()
        self.update_state = label(tr("You're on version {v}", v=VERSION), "muted")
        row.addWidget(self.update_state)
        row.addStretch()
        self.check_btn = button(tr("Check now"), None, 'refresh')
        self.check_btn.clicked.connect(self._check_updates)
        row.addWidget(self.check_btn)
        c.addLayout(row)
        v.addWidget(card)

        # ---------- tools
        v.addSpacing(8)
        v.addWidget(label(tr("CONVERSION ENGINES"), "section"))
        card, c = self._card()
        hint = label(tr("FFmpeg ships with the app. LibreOffice, Pandoc and ImageMagick are optional — "
                        "install them to unlock more document formats."), "subtle")
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
            ok = tool_available(self.cfg.get(key))
            dot = label("●" if ok else "○")
            dot.setStyleSheet(f"color: {theme.colors()['success' if ok else 'subtle']};")
            dot.setToolTip(tr("Found") if ok else tr("Not found"))
            grid.addWidget(dot, r, 0)
            name_lbl = label(name)
            name_lbl.setToolTip(tr(purpose))
            grid.addWidget(name_lbl, r, 1)
            edit = QLineEdit(str(self.cfg.get(key) or ""))
            edit.setPlaceholderText(tr(purpose))
            self.paths[key] = edit
            grid.addWidget(edit, r, 2)
            browse = button("", "icon", 'folder', tooltip=tr("Browse…"))
            browse.clicked.connect(lambda _=False, e=edit: self._browse(e))
            grid.addWidget(browse, r, 3)
        grid.setColumnStretch(2, 1)
        c.addLayout(grid)
        v.addWidget(card)

        # ---------- about
        v.addSpacing(8)
        v.addWidget(label(tr("ABOUT"), "section"))
        card, c = self._card()
        row = QHBoxLayout()
        row.addWidget(label(f"{APP_NAME} {VERSION}"))
        row.addStretch()
        news = button(tr("What's new"), "ghost", 'info')
        news.clicked.connect(self._changelog)
        row.addWidget(news)
        gh = button("GitHub", "ghost", 'github')
        gh.clicked.connect(lambda: webbrowser.open(GITHUB_URL))
        row.addWidget(gh)
        data = button(tr("Data folder"), "ghost", 'folder-open')
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
        cancel = button(tr("Cancel"))
        cancel.clicked.connect(self.reject)
        f.addWidget(cancel)
        save = button(tr("Save"), "primary")
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
        path, _ = QFileDialog.getOpenFileName(self, tr("Select program"), os.path.dirname(edit.text()) or "",
                                              "Programs (*.exe);;All files (*)")
        if path:
            edit.setText(path)

    def _open_data_folder(self):
        from modules.paths import user_dir
        os.startfile(user_dir())

    def _changelog(self):
        from .dialogs import MarkdownDialog
        from modules.changelog import full
        dlg = MarkdownDialog(tr("Changelog"), f"{APP_NAME} {VERSION}", full(), parent=self)
        theme.set_dark_titlebar(dlg)
        dlg.exec()

    def _check_updates(self):
        if not self.main:
            return
        self.check_btn.setEnabled(False)
        self.update_state.setText(tr("Checking…"))

        def done(info, err):
            self.check_btn.setEnabled(True)
            if err:
                self.update_state.setText(tr("Couldn't reach GitHub"))
                self.update_state.setToolTip(err)
            elif info:
                self.update_state.setText(tr("Version {v} is available", v=info.version))
                self.reject()
                self.main.show_update_dialog()
            else:
                self.update_state.setText(tr("You're up to date ({v})", v=VERSION))

        self.main.check_for_updates(silent=False, on_done=done)

    def save(self):
        for key, edit in self.paths.items():
            self.cfg.set(key, edit.text().strip())
        self.cfg.set("theme_mode", self.theme_seg.value())
        self.cfg.set("language", self.lang.currentData())
        self.cfg.set("open_folder_when_done", self.open_done.isChecked())
        self.cfg.set("auto_remove_finished", self.auto_remove.isChecked())
        self.cfg.set("enable_advanced_formats", self.advanced.isChecked())
        self.cfg.set("auto_update", self.auto_update.isChecked())
        if shell_integration.available() and self.ctx.isChecked() != shell_integration.is_enabled():
            try:
                if self.ctx.isChecked():
                    shell_integration.enable(tr("Convert with ypriteConvert"))
                else:
                    shell_integration.disable()
            except OSError:
                pass
        self.accept()
