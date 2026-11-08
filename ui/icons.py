"""Small line icons drawn from inline SVG, tinted to any colour at runtime."""
from functools import lru_cache

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

_PATHS = {
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'x': '<path d="M6 6l12 12M18 6L6 18"/>',
    'check': '<path d="M5 12.5l4.5 4.5L19 7"/>',
    'arrow-right': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'folder': '<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H9l2 2h7.5A2.5 2.5 0 0 1 21 9.5v7A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5z"/>',
    'folder-open': '<path d="M3 17V7.5A2.5 2.5 0 0 1 5.5 5H9l2 2h6.5A2.5 2.5 0 0 1 20 9.5V10"/><path d="M3 17l2.6-6.1A1.5 1.5 0 0 1 7 10h13.2a1 1 0 0 1 .9 1.4L18.6 17.5a2.5 2.5 0 0 1-2.3 1.5H5a2 2 0 0 1-2-2z"/>',
    'settings': '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    'upload': '<path d="M12 15V4M7 9l5-5 5 5"/><path d="M4 15v3.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V15"/>',
    'download': '<path d="M12 4v11M7 10l5 5 5-5"/><path d="M4 20h16"/>',
    'trash': '<path d="M4 7h16M10 11v6M14 11v6M9 7V4.5h6V7M6 7l1 12.5A1.5 1.5 0 0 0 8.5 21h7a1.5 1.5 0 0 0 1.5-1.5L18 7"/>',
    'alert': '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.5v.01"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.5v.01"/>',
    'refresh': '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6"/>',
    'wand': '<path d="M5 19L15 9M14 4v3M19 9h-3M17.5 5.5l-2 2M10 4.5v1.5M19.5 14H18"/>',
    'layers': '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    'image': '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="M21 16l-5-5-9.5 8.5"/>',
    'video': '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M10.2 9.4v5.2l4.3-2.6z" fill="currentColor"/>',
    'audio': '<path d="M9 18V6.5l10-2V16"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    'document': '<path d="M14 3H7.5A2.5 2.5 0 0 0 5 5.5v13A2.5 2.5 0 0 0 7.5 21h9a2.5 2.5 0 0 0 2.5-2.5V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
    'pdf': '<path d="M14 3H7.5A2.5 2.5 0 0 0 5 5.5v13A2.5 2.5 0 0 0 7.5 21h9a2.5 2.5 0 0 0 2.5-2.5V8z"/><path d="M14 3v5h5"/><path d="M8.5 16.5c2-1 4.5-4.5 4-6.5-.4-1.5-2-.5-1.5 1 .7 2.2 3.3 4.7 5 5"/>',
    'unknown': '<path d="M14 3H7.5A2.5 2.5 0 0 0 5 5.5v13A2.5 2.5 0 0 0 7.5 21h9a2.5 2.5 0 0 0 2.5-2.5V8z"/><path d="M14 3v5h5M10 12.5a2 2 0 1 1 2.8 1.8c-.5.3-.8.7-.8 1.2M12 18v.01"/>',
    'github': '<path d="M9 19c-4 1.5-4-2-6-2.5M15 21v-3.5a3 3 0 0 0-.8-2.3c2.8-.3 5.8-1.4 5.8-6.2a4.8 4.8 0 0 0-1.3-3.3 4.5 4.5 0 0 0-.1-3.3s-1.1-.3-3.5 1.3a12 12 0 0 0-6.2 0C6.5 2.1 5.4 2.4 5.4 2.4a4.5 4.5 0 0 0-.1 3.3A4.8 4.8 0 0 0 4 9c0 4.8 3 5.9 5.8 6.2a3 3 0 0 0-.8 2.3V21"/>',
    'more': '<circle cx="5.5" cy="12" r="1.2" fill="currentColor"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/><circle cx="18.5" cy="12" r="1.2" fill="currentColor"/>',
}


def svg(name, color, stroke=1.8):
    body = _PATHS.get(name, _PATHS['unknown']).replace('currentColor', color)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


@lru_cache(maxsize=512)
def pixmap(name, color, size=18, stroke=1.8):
    app = QApplication.instance()
    dpr = app.devicePixelRatio() if app else 1.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg(name, color, stroke).encode()))
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size * dpr, size * dpr))
    painter.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name, color, size=18, stroke=1.8):
    return QIcon(pixmap(name, color, size, stroke))
