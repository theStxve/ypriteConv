import os
import shutil

from PyQt6.QtCore import QThread, pyqtSignal

from modules.file_detect import EffectiveSource, detect
from pipeline_steps.conversion_step import get_converter


def convert_one(src, dest, fmt, quality='medium'):
    """
    Convert a single file. Handles files with custom/wrong extensions by
    detecting the real type from the content. Returns (success, message).
    """
    det = detect(src)

    # "Restore": file is already in the requested format, only the extension was wrong
    if det.real and det.real == fmt and det.mismatch:
        shutil.copy2(src, dest)
        return True, f"Restored as .{fmt} (detected {det.label or det.real.upper()})"

    converter = get_converter(det.effective, fmt)
    if converter is None:
        return False, "Unknown file type - can't detect what this file contains"

    with EffectiveSource(src, det) as real_src:
        success, msg = converter.convert(real_src, dest, fmt, quality=quality)

    if success and det.mismatch:
        msg = f"{msg} (detected {det.label or det.real.upper()})"
    return success, msg


class ConversionWorker(QThread):
    progress = pyqtSignal(int, str, str)  # file id, status, message
    finished_all = pyqtSignal()

    def __init__(self, tasks):
        """
        tasks: list of dicts: {'index': id, 'source': str, 'dest': str, 'format': str, 'quality': str}
        """
        super().__init__()
        self.tasks = tasks
        self.is_running = True

    def run(self):
        for task in self.tasks:
            if not self.is_running:
                self.progress.emit(task['index'], "Cancelled", "Cancelled by user")
                continue

            idx, src, dest, fmt = task['index'], task['source'], task['dest'], task['format']
            self.progress.emit(idx, "Running", "Converting...")

            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                success, msg = convert_one(src, dest, fmt, task.get('quality', 'medium'))
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

        self.finished_all.emit()

    def stop(self):
        self.is_running = False
