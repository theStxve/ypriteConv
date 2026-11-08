import copy
import glob
import json
import os
import shutil
import sys
import threading

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "ffmpeg_path": "ffmpeg",
    "soffice_path": "soffice",  # LibreOffice
    "magick_path": "magick",    # ImageMagick
    "pandoc_path": "pandoc",
    "default_open_path": os.path.expanduser("~"),
    "default_output_path": os.path.expanduser("~"),
    "show_success_popup": True,
    "auto_remove_finished": False,
    "enable_advanced_formats": False,
    "theme_mode": "System",          # System / Light / Dark
    "output_mode": "source",         # source = next to each original, folder = default_output_path
    "open_folder_when_done": False,
    "quality": "medium",
    "auto_update": True,
    "skipped_version": "",
    "language": "System",            # System / en / de
    "onboarded": False,
    "last_seen_version": "",         # for the "What's new" dialog after an update
    "last_targets": {},              # remembered target format per input type
}

from modules.paths import install_dir as _app_dir, user_path, bundled_tool, FROZEN


class ConfigManager:
    """
    Shared configuration. Every ConfigManager() instance reads from the same
    in-memory dict, so the file is loaded (and tools auto-detected) only once
    per process instead of on every single conversion.
    """
    _shared = None
    _lock = threading.RLock()
    first_run = False   # True if no config file existed when the app started

    def __init__(self):
        with ConfigManager._lock:
            if ConfigManager._shared is None:
                ConfigManager._shared = copy.deepcopy(DEFAULT_CONFIG)
                self.config = ConfigManager._shared
                self.load_config()
            self.config = ConfigManager._shared

    def get_config_path(self):
        return user_path(CONFIG_FILE)

    def load_config(self):
        path = self.get_config_path()
        dirty = True
        ConfigManager.first_run = not os.path.exists(path)
        if not os.path.exists(path) and FROZEN:
            # Settings from an older portable build that kept config next to the exe
            legacy = os.path.join(_app_dir(), CONFIG_FILE)
            if os.path.exists(legacy):
                try:
                    shutil.copy2(legacy, path)
                except OSError:
                    pass
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.config.update(data)
                # Old builds stored a purple accent / glass theme settings
                self.config.pop('ui', None)
                if self.config.get('theme_mode') not in ('System', 'Light', 'Dark'):
                    self.config['theme_mode'] = 'System'
                # Only write back if new default keys were missing
                dirty = any(key not in data for key in DEFAULT_CONFIG)
            except Exception as e:
                print(f"Error loading config: {e}")
                dirty = False  # don't overwrite a file we couldn't parse

        if self.auto_detect_tools():
            dirty = True
        if dirty:
            self.save_config()

    def auto_detect_tools(self):
        """Find tools in common Windows locations. Returns True if anything changed."""
        app_path = _app_dir()
        changed = False

        def missing(key):
            p = self.config.get(key)
            return not p or (not shutil.which(p) and not os.path.exists(p))

        def try_set(key, candidates):
            nonlocal changed
            for c in candidates:
                if c and os.path.exists(c):
                    self.config[key] = c
                    changed = True
                    return

        # Prefer the FFmpeg shipped with the installer over whatever is on PATH
        bundled_ffmpeg = bundled_tool('ffmpeg.exe')
        if bundled_ffmpeg and (missing('ffmpeg_path') or self.config.get('ffmpeg_path') == 'ffmpeg'):
            try_set('ffmpeg_path', [bundled_ffmpeg])

        if missing('soffice_path'):
            try_set('soffice_path', [
                os.path.join(app_path, 'bin', 'soffice.exe'),
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ])

        if missing('magick_path'):
            matches = []
            for base in (r"C:\Program Files", r"C:\Program Files (x86)"):
                matches += glob.glob(os.path.join(base, "ImageMagick*", "magick.exe"))
            try_set('magick_path', sorted(matches, reverse=True))

        if missing('pandoc_path'):
            try_set('pandoc_path', [
                os.path.join(app_path, 'bin', 'pandoc.exe'),
                os.path.expandvars(r"%LOCALAPPDATA%\Pandoc\pandoc.exe"),
                r"C:\Program Files\Pandoc\pandoc.exe",
            ])

        return changed

    def save_config(self):
        path = self.get_config_path()
        with ConfigManager._lock:
            try:
                tmp = path + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4)
                os.replace(tmp, path)  # atomic: never leaves a half-written config
            except Exception as e:
                print(f"Error saving config: {e}")

    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        if self.config.get(key) == value:
            return
        self.config[key] = value
        self.save_config()
