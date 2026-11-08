"""Thumbnails and media info (duration) for the file list and video options."""
import io
import re

from PIL import Image, ImageOps

from converters.base_converter import run_tool, tool_available
from modules.config_manager import ConfigManager
from modules.format_rules import FormatRules

try:  # make sure HEIC opens here too
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def _to_png_bytes(img, size):
    img = ImageOps.exif_transpose(img)
    img = ImageOps.fit(img.convert('RGBA') if img.mode in ('RGBA', 'LA', 'P') else img.convert('RGB'),
                       (size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def thumbnail(path, real_format, size=96):
    """PNG bytes of a square thumbnail, or None if not possible."""
    fmt = (real_format or '').lower()
    try:
        if fmt == 'pdf':
            import fitz
            with fitz.open(path) as doc:
                if doc.page_count == 0 or doc.needs_pass:
                    return None
                page = doc[0]
                zoom = size * 2 / max(page.rect.width, page.rect.height)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                # documents: show the top of the page instead of the centre
                return _to_png_bytes(img.crop((0, 0, img.width, min(img.height, img.width))), size)

        category = FormatRules.get_category(fmt)
        if category == 'image':
            with Image.open(path) as img:
                img.draft('RGB', (size * 2, size * 2))  # fast JPEG decode at reduced size
                img.seek(0)
                img.load()
                return _to_png_bytes(img, size)

        if category == 'video':
            ffmpeg = ConfigManager().get('ffmpeg_path')
            if not tool_available(ffmpeg):
                return None
            import subprocess, sys
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            for seek in ('1', '0'):
                r = subprocess.run([ffmpeg, '-v', 'error', '-ss', seek, '-i', path, '-frames:v', '1',
                                    '-vf', f'scale={size * 2}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                                   capture_output=True, timeout=20, creationflags=flags)
                if r.returncode == 0 and r.stdout:
                    with Image.open(io.BytesIO(r.stdout)) as img:
                        return _to_png_bytes(img, size)
    except Exception:
        return None
    return None


_DUR = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def duration(path):
    """Media duration in seconds (via FFmpeg), or None."""
    ffmpeg = ConfigManager().get('ffmpeg_path')
    if not tool_available(ffmpeg):
        return None
    try:
        _code, out = run_tool([ffmpeg, '-hide_banner', '-i', path], timeout=20)
    except Exception:
        return None
    m = _DUR.search(out)
    if not m:
        return None
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def parse_time(text):
    """'1:23', '01:02:03', '83', '83.5' -> seconds (float), '' -> None. Raises ValueError."""
    text = (text or '').strip().replace(',', '.')
    if not text:
        return None
    parts = text.split(':')
    if len(parts) > 3:
        raise ValueError(text)
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + float(p)
    if seconds < 0:
        raise ValueError(text)
    return seconds


def format_time(seconds):
    if seconds is None:
        return ''
    seconds = max(0, seconds)
    h, rem = divmod(int(round(seconds)), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
