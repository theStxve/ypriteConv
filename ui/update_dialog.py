from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QProgressBar, QMessageBox

from app_info import VERSION
from modules.updater import UpdateDownloader, launch_installer
from .widgets import label, button


class UpdateDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self.skipped = False
        self.installer_started = False
        self.downloader = None
        self.setWindowTitle("Update available")
        self.setMinimumSize(520, 420)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 20)
        v.setSpacing(8)
        v.addWidget(label(f"Version {info.version} is available", "h1"))
        sub = label(f"You have {VERSION}. The update installs in the background and "
                    "the app restarts by itself.", "muted")
        sub.setWordWrap(True)
        v.addWidget(sub)
        v.addSpacing(8)
        v.addWidget(label("WHAT'S NEW", "section"))
        notes = QTextBrowser()
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(info.notes.strip() or "_No release notes._")
        v.addWidget(notes, 1)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        v.addWidget(self.progress)
        self.state = label("", "subtle")
        v.addWidget(self.state)

        row = QHBoxLayout()
        self.skip_btn = button("Skip this version", "ghost")
        self.skip_btn.clicked.connect(self._skip)
        row.addWidget(self.skip_btn)
        row.addStretch()
        self.later_btn = button("Later")
        self.later_btn.clicked.connect(self.reject)
        row.addWidget(self.later_btn)
        self.install_btn = button("Install update", "primary")
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
        self.state.setText("Downloading…")
        self.downloader = UpdateDownloader(self.info)
        self.downloader.progress.connect(self._progress)
        self.downloader.done.connect(self._downloaded)
        self.downloader.failed.connect(self._failed)
        self.downloader.start()

    def _progress(self, done, total):
        if total:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
            self.state.setText(f"Downloading…  {done / 1048576:.1f} / {total / 1048576:.1f} MB")

    def _downloaded(self, path):
        self.state.setText("Starting installer…")
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
        QMessageBox.warning(self, "Update failed", f"The update couldn't be downloaded.\n\n{err}")

    def reject(self):
        if self.downloader and self.downloader.isRunning():
            self.downloader.cancel()
            self.downloader.wait(3000)
        super().reject()
