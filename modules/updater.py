"""
Auto-update via GitHub Releases.

Release convention (the GitHub Action produces this automatically):
  tag:   v1.2.3
  asset: ypriteConvert-Setup-1.2.3.exe   (Inno Setup installer)

Flow: check latest release -> newer than VERSION? -> download installer to temp
-> verify size (+ SHA-256 when GitHub provides it) -> run installer silently
-> app quits, installer replaces files and restarts the app.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from app_info import APP_NAME, GITHUB_REPO, VERSION, version_tuple

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"{APP_NAME}-updater/{VERSION}"
ASSET_PATTERN = re.compile(r"setup.*\.exe$", re.IGNORECASE)


@dataclass
class UpdateInfo:
    version: str
    notes: str
    url: str
    size: int
    sha256: str
    page: str


def _get_json(url, timeout=10):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/vnd.github+json',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_latest():
    """Return UpdateInfo if a newer release with an installer exists, else None."""
    data = _get_json(API_URL)
    if data.get('draft') or data.get('prerelease'):
        return None
    tag = data.get('tag_name', '')
    if version_tuple(tag) <= version_tuple(VERSION):
        return None
    for asset in data.get('assets', []):
        if ASSET_PATTERN.search(asset.get('name', '')):
            digest = asset.get('digest') or ''
            return UpdateInfo(
                version=tag.lstrip('vV'),
                notes=data.get('body') or '',
                url=asset['browser_download_url'],
                size=int(asset.get('size') or 0),
                sha256=digest.split(':', 1)[1].lower() if digest.startswith('sha256:') else '',
                page=data.get('html_url', ''),
            )
    return None


class UpdateChecker(QThread):
    result = pyqtSignal(object)   # UpdateInfo or None
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.result.emit(fetch_latest())
        except Exception as e:
            self.failed.emit(str(e))


class UpdateDownloader(QThread):
    progress = pyqtSignal(int, int)   # bytes done, total
    done = pyqtSignal(str)            # path to verified installer
    failed = pyqtSignal(str)

    def __init__(self, info: UpdateInfo):
        super().__init__()
        self.info = info
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        target = os.path.join(tempfile.gettempdir(), f"{APP_NAME}-Setup-{self.info.version}.exe")
        part = target + ".part"
        try:
            req = urllib.request.Request(self.info.url, headers={'User-Agent': USER_AGENT})
            sha = hashlib.sha256()
            done = 0
            with urllib.request.urlopen(req, timeout=30) as r, open(part, 'wb') as f:
                total = int(r.headers.get('Content-Length') or self.info.size or 0)
                while True:
                    if self._cancel:
                        raise RuntimeError("Download cancelled")
                    chunk = r.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    sha.update(chunk)
                    done += len(chunk)
                    self.progress.emit(done, total)

            if self.info.size and done != self.info.size:
                raise RuntimeError(f"Download incomplete ({done} of {self.info.size} bytes)")
            if self.info.sha256 and sha.hexdigest() != self.info.sha256:
                raise RuntimeError("Checksum mismatch - the download is corrupted or was tampered with")

            os.replace(part, target)
            self.done.emit(target)
        except Exception as e:
            try:
                os.remove(part)
            except OSError:
                pass
            self.failed.emit(str(e))


def launch_installer(path):
    """
    Start the installer detached. /SILENT shows a small progress window,
    the installer closes this app if needed and relaunches it when done ([Run] entry with Check: WizardSilent).
    """
    flags = 0
    if sys.platform == 'win32':
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([path, '/SILENT', '/SP-', '/NOCANCEL', '/CLOSEAPPLICATIONS'],
                     creationflags=flags, close_fds=True)
