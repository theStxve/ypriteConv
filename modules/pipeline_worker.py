"""
Pipeline Worker - Execute pipelines in background thread

Integrates pipeline system with Qt threading for GUI responsiveness.
"""
from PyQt6.QtCore import QThread, pyqtSignal


class PipelineWorker(QThread):
    """Background worker for pipeline execution"""

    progress = pyqtSignal(int, str, str)  # file id, status, message
    finished_all = pyqtSignal()

    def __init__(self, tasks, pipeline):
        """
        Args:
            tasks: List of dicts with 'index', 'source', 'dest'
            pipeline: Pipeline instance to execute
        """
        super().__init__()
        self.tasks = tasks
        self.pipeline = pipeline
        self.is_running = True

    def run(self):
        for task in self.tasks:
            index = task['index']
            if not self.is_running:
                self.progress.emit(index, "Cancelled", "Cancelled by user")
                continue

            self.progress.emit(index, "Running", f"Running pipeline: {self.pipeline.name}")
            try:
                success, message = self.pipeline.execute(task['source'], task['dest'])
                if success and self.pipeline.last_output_file:
                    task['dest'] = self.pipeline.last_output_file
                self.progress.emit(index, "Done" if success else "Error", message)
            except Exception as e:
                self.progress.emit(index, "Error", f"Error: {e}")

        self.finished_all.emit()

    def stop(self):
        self.is_running = False
