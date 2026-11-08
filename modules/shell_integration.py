"""Explorer right-click entry ("Convert with ypriteConvert"), per user, no admin needed.

Uses the same registry keys as the installer task, so both stay in sync.
"""
import sys

from modules.paths import FROZEN

KEYS = (r"Software\Classes\*\shell\ypriteConvert", r"Software\Classes\Directory\shell\ypriteConvert")


def available():
    """Only the installed exe can register itself (dev runs would point at python.exe)."""
    return FROZEN and sys.platform == 'win32'


def is_enabled():
    if sys.platform != 'win32':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEYS[0] + r"\command"):
            return True
    except OSError:
        return False


def enable(label):
    import winreg
    exe = sys.executable
    for key in KEYS:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, label)
            winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, f'"{exe}",0')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key + r"\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}" "%1"')


def disable():
    import winreg
    for key in KEYS:
        for sub in (key + r"\command", key):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except OSError:
                pass
