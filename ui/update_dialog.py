from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QProgressBar, QMessageBox

from app_info import VERSION
from modules.updater import UpdateDownloader, launch_installer
from .i18n import tr
from .widgets import label, button


class UpdateDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self.skipped = False
        self.installer_started = False
        self.downloader = None
        self.setWindowTitle(tr("Update available"))
        self.setMinimumSize(520, 420)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 20)
        v.setSpacing(8)
        v.addWidget(label(tr("Version {v} is available", v=info.version), "h1"))
        sub = label(tr("You have {v}. The update installs in the background and the app restarts by itself.",
                       v=VERSION), "muted")
        sub.setWordWrap(True)
        v.addWidget(sub)
        v.addSpacing(8)
        v.addWidget(label(tr("WHAT'S NEW"), "section"))
        notes = QTextBrowser()
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(info.notes.strip() or tr("_No release notes._"))
        v.addWidget(notes, 1)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        v.addWidget(self.progress)
        self.state = label("", "subtle")
        v.addWidget(self.state)

        row = QHBoxLayout()
        self.skip_btn = button(tr("Skip this version"), "ghost")
        self.skip_btn.clicked.connect(self._skip)
        row.addWidget(self.skip_btn)
        row.addStretch()
        self.later_btn = button(tr("Later"))
        self.later_btn.clicked.connect(self.reject)
        row.addWidget(self.later_btn)
        self.install_btn = button(tr("Install update"), "primary")
        self.install_btn.clicked.connect(self._install)
        row.addWidget(self.install_btn)
        v.addLayout(row)

    def _skip(self):
        self.skipped = True
        self.reject()

    def _install(self):
        self.install_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress.show()
        self.progress.setRange(0, 0)
        self.state.setText(tr("Downloading…"))
        self.downloader = UpdateDownloader(self.info)
        self.downloader.progress.connect(self._progress)
        self.downloader.done.connect(self._downloaded)
        self.downloader.failed.connect(self._failed)
        self.downloader.start()

    def _progress(self, done, total):
        if total:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
            self.state.setText(tr("Downloading…  {done} / {total} MB", done=f"{done / 1048576:.1f}", total=f"{total / 1048576:.1f}"))

    def _downloaded(self, path):
        self.state.setText(tr("Starting installer…"))
        try:
            launch_installer(path)
        except Exception as e:
            self._failed(f"Couldn't start the installer: {e}")
            return
        self.installer_started = True
        self.accept()

    def _failed(self, err):
        self.progress.hide()
        self.state.setText("")
        self.install_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        QMessageBox.warning(self, tr("Update failed"), tr("The update couldn't be downloaded.\n\n{err}", err=err))

    def reject(self):
        if self.downloader and self.downloader.isRunning():
            self.downloader.cancel()
            self.downloader.wait(3000)
        super().reject()
