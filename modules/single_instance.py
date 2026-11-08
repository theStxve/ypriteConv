"""
Only one window: when the app is started again (e.g. selecting 10 files in
Explorer -> "Convert with ypriteConvert" starts 10 processes), the new process
hands its file paths to the running window and exits.
"""
import getpass
import json

from PyQt6.QtCore import QByteArray
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance:
    def __init__(self, app_name):
        try:
            user = getpass.getuser()
        except Exception:
            user = "user"
        self.name = f"{app_name}-{user}".replace(' ', '_')
        self.server = None
        self._callback = None

    def forward_to_running(self, paths, timeout=400):
        """True if another instance is running (paths were sent to it)."""
        sock = QLocalSocket()
        sock.connectToServer(self.name)
        if not sock.waitForConnected(timeout):
            return False
        sock.write(QByteArray(json.dumps(paths).encode('utf-8')))
        sock.flush()
        sock.waitForBytesWritten(timeout)
        sock.disconnectFromServer()
        return True

    def listen(self, callback):
        self._callback = callback
        self.server = QLocalServer()
        QLocalServer.removeServer(self.name)  # stale socket after a crash
        self.server.listen(self.name)
        self.server.newConnection.connect(self._on_connection)

    def _on_connection(self):
        sock = self.server.nextPendingConnection()
        if sock is None:
            return
        buf = bytearray()

        def read():
            buf.extend(bytes(sock.readAll()))

        def done():
            read()
            try:
                paths = json.loads(buf.decode('utf-8') or '[]')
            except ValueError:
                paths = []
            if self._callback:
                self._callback([p for p in paths if isinstance(p, str)])
            sock.deleteLater()

        sock.readyRead.connect(read)
        sock.disconnected.connect(done)
