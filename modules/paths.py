"""
Where things live, for both dev (python main.py) and the installed app.

- resource_dir: read-only files shipped with the app (assets, built-in presets)
- install_dir:  folder of the exe (bundled tools in bin/)
- user_dir:     writable per-user data (config, custom presets, logs)
"""
import os
import sys

from app_info import APP_NAME

FROZEN = getattr(sys, 'frozen', False)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def install_dir():
    return os.path.dirname(sys.executable) if FROZEN else _PROJECT_ROOT


def resource_dir():
    return getattr(sys, '_MEIPASS', _PROJECT_ROOT) if FROZEN else _PROJECT_ROOT


def resource(*parts):
    return os.path.join(resource_dir(), *parts)


def user_dir():
    if not FROZEN:
        # Dev mode keeps using the project folder, like before
        return _PROJECT_ROOT
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def user_path(*parts):
    return os.path.join(user_dir(), *parts)


def bundled_tool(exe_name):
    """Path of a tool shipped in bin/ (installer puts it next to the exe), or None."""
    for base in (install_dir(), resource_dir(), _PROJECT_ROOT):
        p = os.path.join(base, 'bin', exe_name)
        if os.path.isfile(p):
            return p
    return None
