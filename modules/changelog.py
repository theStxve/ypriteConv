"""Read CHANGELOG.md (shipped with the app) for 'What's new' and the about view."""
import os
import re

from modules.paths import resource


def _text():
    try:
        with open(resource('CHANGELOG.md'), encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ""


def section(version, text=None):
    text = _text() if text is None else text
    m = re.search(rf"^## {re.escape(version.lstrip('vV'))}\s*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return m.group(1).strip() if m else ""


def full():
    """Changelog without the top-level heading."""
    return re.sub(r"^# .*\n+", "", _text(), count=1).strip()
