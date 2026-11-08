import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QThread, pyqtSignal

from modules.file_detect import EffectiveSource, detect
from modules.format_rules import FormatRules
from pipeline_steps.conversion_step import get_converter


def convert_one(src, dest, fmt, quality='medium', **extra):
    """
    Convert a single file. Handles files with custom/wrong extensions by
    detecting the real type from the content. Returns (success, message).
    """
    det = detect(src)

    # "Restore": file is already in the requested format, only the extension was wrong
    if det.real and det.real == fmt and det.mismatch and not extra.get('video_options'):
        shutil.copy2(src, dest)
        return True, f"Restored as .{fmt} (detected {det.label or det.real.upper()})"

    converter = get_converter(det.effective, fmt)
    if converter is None:
        return False, "Unknown file type - can't detect what this file contains"

    with EffectiveSource(src, det) as real_src:
        success, msg = converter.convert(real_src, dest, fmt, quality=quality, **extra)

    if success and det.mismatch:
        msg = f"{msg} (detected {det.label or det.real.upper()})"
    return success, msg


def _parallel_slots():
    cores = os.cpu_count() or 4
    return max(2, min(6, cores // 2))


class ConversionWorker(QThread):
    """
    Converts many files at once. Images/documents run in parallel; FFmpeg jobs
    (video/audio) run one at a time since FFmpeg already uses every core.
    """
    progress = pyqtSignal(object, str, str)  # file id, status, message
    finished_all = pyqtSignal()

    def __init__(self, tasks):
        """
        tasks: list of dicts: {'index': id, 'source', 'dest', 'format', 'quality', 'video_options'?}
        """
        super().__init__()
        self.tasks = tasks
        self.is_running = True
        self._ffmpeg_lock = threading.Lock()

    def _run_task(self, task):
        idx = task['index']
        if not self.is_running:
            self.progress.emit(idx, "Cancelled", "Cancelled")
            return
        src, dest, fmt = task['source'], task['dest'], task['format']

        heavy = FormatRules.get_category(detect(src).effective) in ('video', 'audio')
        lock = self._ffmpeg_lock if heavy else None
        if lock:
            lock.acquire()
        try:
            if not self.is_running:
                self.progress.emit(idx, "Cancelled", "Cancelled")
                return
            self.progress.emit(idx, "Running", "")
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                extra = {'video_options': task['video_options']} if task.get('video_options') else {}
                success, msg = convert_one(src, dest, fmt, task.get('quality', 'medium'), **extra)
            except Exception as e:  # never let one file kill the whole batch
                success, msg = False, f"Unexpected error: {e}"

            # Multi-page PDF -> images writes name_1.ext etc. instead of dest
            if success and not os.path.exists(dest):
                base, ext = os.path.splitext(dest)
                if os.path.exists(f"{base}_1{ext}"):
                    task['dest'] = f"{base}_1{ext}"
                else:
                    success, msg = False, "Converter reported success but no output file was created"
            self.progress.emit(idx, "Done" if success else "Error", msg)
        finally:
            if lock:
                lock.release()

    def run(self):
        with ThreadPoolExecutor(max_workers=_parallel_slots()) as pool:
            list(pool.map(self._run_task, self.tasks))
        self.finished_all.emit()

    def stop(self):
        self.is_running = False
