import os
import sys


def _is_cli(args):
    # Any "--flag" means command-line mode; plain paths (Explorer "Open with") open the GUI
    return any(a.startswith('-') for a in args)


def _attach_console():
    """The installed exe has no console; reattach to the calling terminal for CLI output."""
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return
    try:
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):
            sys.stdout = open('CONOUT$', 'w', encoding='utf-8', errors='replace')
            sys.stderr = sys.stdout
            sys.stdin = open('CONIN$', 'r')
    except Exception:
        pass


def _setup_logging():
    import logging
    import traceback
    from modules.paths import user_path, FROZEN

    log_dir = user_path('logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    try:  # keep the log small
        if os.path.getsize(log_file) > 2_000_000:
            os.replace(log_file, log_file + '.1')
    except OSError:
        pass
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')

    if FROZEN and sys.stdout is None:
        # Windowed exe: send print() output from converters to the log
        class _LogWriter:
            def write(self, s):
                if s.strip():
                    logging.info(s.rstrip())

            def flush(self):
                pass
        sys.stdout = sys.stderr = _LogWriter()

    def excepthook(exc_type, exc, tb):
        text = ''.join(traceback.format_exception(exc_type, exc, tb))
        logging.error("Uncaught exception:\n%s", text)
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                QMessageBox.critical(None, "Something went wrong",
                                     f"{exc}\n\nDetails were saved to:\n{log_file}")
        except Exception:
            pass
    sys.excepthook = excepthook


def run_gui(paths):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    from app_info import APP_NAME, APP_ID, VERSION, PUBLISHER
    from modules.single_instance import SingleInstance
    from modules.paths import resource

    if sys.platform == 'win32':
        try:  # own taskbar identity/icon instead of python.exe's
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName(PUBLISHER)
    app.setWindowIcon(QIcon(resource('assets', 'icon.ico')))

    instance = SingleInstance(APP_NAME)
    if instance.forward_to_running(paths):
        return 0  # an open window received the files

    from modules.config_manager import ConfigManager
    from ui import theme
    from ui.main_window import MainWindow

    from ui.i18n import set_language
    set_language(ConfigManager().get("language") or "System")
    theme.apply(ConfigManager().get("theme_mode") or "System")
    window = MainWindow()
    instance.listen(window.receive_paths)
    window.show()
    if paths:
        window.add_paths(paths)
    return app.exec()


def main():
    args = sys.argv[1:]
    if _is_cli(args):
        _attach_console()
        from cli import main as cli_main
        cli_main()
        return
    _setup_logging()
    sys.exit(run_gui([os.path.abspath(a) for a in args]))


if __name__ == '__main__':
    main()
