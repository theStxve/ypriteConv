"""
Content-based file type detection.

Files with made-up or wrong extensions (photo.yprite, clip.asdf, image.jpg that is
really a PNG) are identified by their first bytes ("magic numbers"), so they can
still be converted, or simply restored to their real extension.
"""
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass

from modules.format_rules import FormatRules

# Extensions that mean the same thing
ALIASES = {'jpeg': 'jpg', 'tif': 'tiff', 'heif': 'heic', 'htm': 'html', 'markdown': 'md', 'm4v': 'mp4', 'mpeg': 'mpg'}


def norm_ext(ext):
    e = (ext or '').lower().lstrip('.')
    return ALIASES.get(e, e)


@dataclass
class Detection:
    ext: str            # extension as written on the file ('' if none), normalized
    real: str           # detected real format ('' if unknown), normalized
    label: str = ''     # human readable, e.g. "PNG image"

    @property
    def effective(self):
        """Format to treat the file as."""
        return self.real or self.ext

    @property
    def mismatch(self):
        """True if the content doesn't match the extension (custom/wrong extension)."""
        return bool(self.real) and self.real != self.ext and not _compatible(self.real, self.ext)


def _compatible(real, ext):
    # Containers that legitimately share a signature
    groups = [{'mp4', 'mov', 'm4a', '3gp'}, {'mkv', 'webm'}, {'txt', 'md', 'html'},
              {'ogg', 'opus'}, {'wma', 'wmv'}, {'zip', 'docx', 'odt'}]
    return any(real in g and ext in g for g in groups)


def _ftyp(head):
    if head[4:8] != b'ftyp':
        return None
    brand = head[8:12]
    brands = head[8:64]
    if brand in (b'heic', b'heix', b'heim', b'heis', b'hevc', b'hevx', b'mif1', b'msf1'):
        return 'heic', 'HEIC image'
    if brand in (b'avif', b'avis'):
        return 'avif', 'AVIF image'
    if brand in (b'M4A ', b'M4B ', b'M4P ') or b'M4A ' in brands:
        return 'm4a', 'M4A audio'
    if brand == b'qt  ':
        return 'mov', 'QuickTime video'
    if brand.startswith(b'3g'):
        return '3gp', '3GP video'
    return 'mp4', 'MP4 video'


def _zip_kind(path):
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if 'mimetype' in names:
                mt = z.read('mimetype').decode('ascii', 'ignore')
                if 'opendocument.text' in mt:
                    return 'odt', 'OpenDocument text'
                if 'epub' in mt:
                    return 'epub', 'EPUB e-book'
            if 'word/document.xml' in names:
                return 'docx', 'Word document'
            if 'xl/workbook.xml' in names:
                return 'xlsx', 'Excel workbook'
            if 'ppt/presentation.xml' in names:
                return 'pptx', 'PowerPoint presentation'
    except Exception:
        pass
    return 'zip', 'ZIP archive'


def _text_kind(head):
    try:
        text = head.decode('utf-8')
    except UnicodeDecodeError:
        # allow a cut-off multibyte char at the end of the sample
        try:
            text = head[:-3].decode('utf-8')
        except UnicodeDecodeError:
            return None
    if '\x00' in text:
        return None
    t = text.lstrip('﻿').lstrip().lower()
    if t.startswith('{\\rtf'):
        return 'rtf', 'RTF document'
    if t.startswith('<!doctype html') or t.startswith('<html') or '<body' in t[:2000]:
        return 'html', 'HTML document'
    if t.startswith('<?xml') or t.startswith('<svg'):
        if '<svg' in t[:2000]:
            return 'svg', 'SVG image'
        return None
    md_hints = ('# ', '## ', '- ', '* ', '```', '[', '> ')
    lines = [l for l in text.splitlines()[:40] if l.strip()]
    if lines and sum(l.lstrip().startswith(md_hints) for l in lines) >= max(2, len(lines) // 5):
        return 'md', 'Markdown text'
    printable = sum(ch.isprintable() or ch in '\r\n\t' for ch in text)
    if text and printable / len(text) > 0.97:
        return 'txt', 'Plain text'
    return None


def sniff(path):
    """Return (real_ext, label) from file content, or ('', '') if unknown."""
    try:
        with open(path, 'rb') as f:
            head = f.read(4096)
    except OSError:
        return '', ''
    if not head:
        return '', ''

    h = head
    if h.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png', 'PNG image'
    if h.startswith(b'\xff\xd8\xff'):
        return 'jpg', 'JPEG image'
    if h[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif', 'GIF image'
    if h.startswith(b'BM') and len(h) > 14 and h[6:10] == b'\x00\x00\x00\x00':
        return 'bmp', 'BMP image'
    if h[:4] in (b'II*\x00', b'MM\x00*'):
        return 'tiff', 'TIFF image'
    if h[:4] == b'\x00\x00\x01\x00':
        return 'ico', 'Icon'
    if h.startswith(b'%PDF'):
        return 'pdf', 'PDF document'
    if h[:4] == b'RIFF':
        kind = h[8:12]
        if kind == b'WEBP':
            return 'webp', 'WebP image'
        if kind == b'WAVE':
            return 'wav', 'WAV audio'
        if kind == b'AVI ':
            return 'avi', 'AVI video'
    ft = _ftyp(h)
    if ft:
        return ft
    if h.startswith(b'\x1a\x45\xdf\xa3'):
        return ('webm', 'WebM video') if b'webm' in h[:64] else ('mkv', 'Matroska video')
    if h.startswith(b'fLaC'):
        return 'flac', 'FLAC audio'
    if h.startswith(b'OggS'):
        return ('opus', 'Opus audio') if b'OpusHead' in h[:200] else ('ogg', 'Ogg audio')
    if h.startswith(b'ID3') or (len(h) > 1 and h[0] == 0xFF and (h[1] & 0xE0) == 0xE0 and (h[1] & 0x06) != 0):
        # 0xFFF? frame sync; layer bits != 0 excludes AAC ADTS (layer 00)
        return 'mp3', 'MP3 audio'
    if len(h) > 1 and h[0] == 0xFF and (h[1] & 0xF6) == 0xF0:
        return 'aac', 'AAC audio'
    if h.startswith(b'\x30\x26\xb2\x75\x8e\x66\xcf\x11'):
        return 'wmv', 'Windows Media file'
    if h.startswith(b'FLV'):
        return 'flv', 'Flash video'
    if h[:4] in (b'\x00\x00\x01\xba', b'\x00\x00\x01\xb3'):
        return 'mpg', 'MPEG video'
    if h.startswith(b'PK\x03\x04'):
        return _zip_kind(path)
    if h.startswith(b'\xd0\xcf\x11\xe0'):
        return 'doc', 'Legacy Office document'
    text = _text_kind(h)
    if text:
        return text
    return '', ''


# Formats we sniff: always trust content for these; for unknown extensions this
# is the only information we have.
_KNOWN_BY_EXT = set(FormatRules.DOC_FORMATS + FormatRules.IMAGE_FORMATS
                    + FormatRules.AUDIO_FORMATS + FormatRules.VIDEO_FORMATS + ['pdf'])


def detect(path):
    ext = norm_ext(os.path.splitext(path)[1])
    real, label = sniff(path)
    real = norm_ext(real)
    if real in ('txt',) and ext in ('md', 'html', 'csv', 'json', 'xml', 'log', 'py', 'srt'):
        real = ext  # plain-text heuristics are weak, trust a text-ish extension
    if not real and ext in _KNOWN_BY_EXT:
        real = ext
    return Detection(ext=ext, real=real, label=label)


def convertible(fmt):
    return fmt == 'pdf' or FormatRules.get_category(fmt) != 'unknown'


def target_options(det):
    """
    [(format, label), ...] for a detected file. For files with a custom/wrong
    extension the first option restores the real extension (lossless copy).
    """
    options = []
    if det.mismatch and det.real:
        options.append((det.real, f"{det.real} · restore"))
    for t in FormatRules.get_target_formats(det.effective):
        if norm_ext(t) != det.effective and all(t != o[0] for o in options):
            options.append((t, t))
    # Videos: allow re-encoding into the same format (to rotate, trim, shrink, ...)
    if FormatRules.get_category(det.effective) == 'video' and not det.mismatch \
            and det.effective in FormatRules.get_target_formats(det.effective) + ['mov', 'avi']:
        options.append((det.effective, f"{det.effective} · keep format"))
    return options


class EffectiveSource:
    """
    Context manager: gives converters a path whose extension matches the real
    content (needed by tools like Pandoc/LibreOffice that look at extensions).
    Uses a hard link when possible (instant, no extra disk space), else a copy.
    """

    def __init__(self, path, detection=None):
        self.path = path
        self.det = detection or detect(path)
        self._tmp = None

    def __enter__(self):
        if not self.det.mismatch and self.det.ext:
            return self.path
        if not self.det.real:
            return self.path
        self._tmp = tempfile.mkdtemp(prefix="yprite_src_")
        base = os.path.splitext(os.path.basename(self.path))[0] or 'file'
        target = os.path.join(self._tmp, f"{base}.{self.det.real}")
        try:
            os.link(self.path, target)
        except OSError:
            shutil.copy2(self.path, target)
        return target

    def __exit__(self, *exc):
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
        return False
