import os
import shutil
import subprocess
import sys

# Hide console windows for child processes on Windows
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


def tool_available(path):
    """True if an external tool exists as a file or on PATH."""
    return bool(path) and (os.path.isfile(path) or shutil.which(path) is not None)


def run_tool(cmd, timeout=None):
    """
    Run an external tool without a console window.
    Returns (returncode, combined_error_text).
    Output is decoded as UTF-8 with replacement so odd bytes in
    FFmpeg/LibreOffice output can never crash the conversion.
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=_NO_WINDOW,
        timeout=timeout,
    )
    return result.returncode, (result.stderr or '') + (result.stdout or '')


def short_error(text, max_lines=6):
    """Keep only the last meaningful lines of a tool's error output."""
    lines = [l for l in (text or '').strip().splitlines() if l.strip()]
    return '\n'.join(lines[-max_lines:]) if lines else 'Unknown error'


class BaseConverter:
    def convert(self, source, dest, target_format, **kwargs):
        """
        Convert source file to dest file with target_format.
        Returns:
            (bool, str): (Success, Message)
        """
        raise NotImplementedError
