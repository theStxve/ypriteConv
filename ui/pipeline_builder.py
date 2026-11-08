"""
Pipeline Builder Dialog - Create custom pipelines visually
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QLabel, QLineEdit, QComboBox,
                             QMessageBox, QSplitter, QGroupBox, QFormLayout,
                             QScrollArea, QWidget)
from PyQt6.QtCore import Qt

from modules.pipeline_engine import Pipeline
from pipeline_steps import StepRegistry, ConversionStep, ExtractAudioStep, NormalizeAudioStep
from modules.pipeline_serializer import PresetLibrary

class PipelineBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pipeline Builder")
        self.resize(1000, 700)
        self.pipeline = Pipeline("New Custom Pipeline")
        self.current_editing_step = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header: Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Pipeline Name:"))
        self.name_edit = QLineEdit(self.pipeline.name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Main Area Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: Library
        left_group = QGroupBox("1. Step Library")
        left_layout = QVBoxLayout(left_group)
        self.library_list = QListWidget()
        self.library_list.addItems(["Conversion Step", "Extract Audio", "Normalize Audio"])
        self.library_list.setDragEnabled(False)
        self.library_list.itemDoubleClicked.connect(self.add_step_from_list)
        left_layout.addWidget(self.library_list)
        left_layout.addWidget(QLabel("Double-click to add"))
        splitter.addWidget(left_group)

        # MIDDLE: Pipeline Steps
        mid_group = QGroupBox("2. Pipeline Steps")
        mid_layout = QVBoxLayout(mid_group)
        self.steps_list = QListWidget()
        self.steps_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.steps_list.itemClicked.connect(self.load_step_config)
        mid_layout.addWidget(self.steps_list)

        # Step Controls
        step_btns = QHBoxLayout()
        up_btn = QPushButton("▲")
        up_btn.clicked.connect(self.move_step_up)
        down_btn = QPushButton("▼")
        down_btn.clicked.connect(self.move_step_down)
        remove_btn = QPushButton("🗑️")
        remove_btn.clicked.connect(self.remove_step)

        step_btns.addWidget(up_btn)
        step_btns.addWidget(down_btn)
        step_btns.addWidget(remove_btn)
        mid_layout.addLayout(step_btns)

        splitter.addWidget(mid_group)

        # RIGHT: Configuration
        right_group = QGroupBox("3. Configure Step")
        right_layout = QVBoxLayout(right_group)

        self.config_area = QScrollArea()
        self.config_area.setWidgetResizable(True)
        self.config_widget = QWidget()
        self.config_form = QFormLayout(self.config_widget)
        self.config_area.setWidget(self.config_widget)

        right_layout.addWidget(self.config_area)
        self.apply_config_btn = QPushButton("Apply Changes")
        self.apply_config_btn.clicked.connect(self.apply_step_config)
        self.apply_config_btn.setEnabled(False)
        right_layout.addWidget(self.apply_config_btn)

        splitter.addWidget(right_group)

        splitter.setSizes([200, 300, 300])
        layout.addWidget(splitter)

        # Footer Actions
        action_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save Preset")
        save_btn.clicked.connect(self.save_pipeline)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        action_layout.addStretch()
        action_layout.addWidget(save_btn)
        action_layout.addWidget(close_btn)
        layout.addLayout(action_layout)

    def add_step_from_list(self, item):
        if not item: return
        step_type = item.text()
        step = None

        if step_type == "Conversion Step":
            step = ConversionStep(step_id=f"convert_{len(self.pipeline.steps) + 1}", name="Convert File")
            step.configure(target_format="mp4", quality="medium")
        elif step_type == "Extract Audio":
            step = ExtractAudioStep(step_id=f"extract_audio_{len(self.pipeline.steps) + 1}", name="Extract Audio")
            step.configure(audio_format="mp3")
        elif step_type == "Normalize Audio":
            step = NormalizeAudioStep(step_id=f"normalize_{len(self.pipeline.steps) + 1}", name="Normalize")
            step.configure(target_lufs=-16.0)

        if step:
            self.pipeline.add_step(step)
            self.refresh_steps_list()
            # Select the new item
            self.steps_list.setCurrentRow(len(self.pipeline.steps)-1)
            self.load_step_config(self.steps_list.currentItem())

    def refresh_steps_list(self):
        current_row = self.steps_list.currentRow()
        self.steps_list.clear()
        for i, step in enumerate(self.pipeline.steps):
            self.steps_list.addItem(f"{i+1}. {step.name}")

        if current_row >= 0 and current_row < self.steps_list.count():
            self.steps_list.setCurrentRow(current_row)

    def load_step_config(self, item):
        if not item:
            self.clear_config_form()
            return

        row = self.steps_list.row(item)
        if row == -1: return

        step = self.pipeline.steps[row]
        self.current_editing_step = step

        self.clear_config_form()
        self.apply_config_btn.setEnabled(True)

        # Build form based on step type
        # Name field (always present)
        name_edit = QLineEdit(step.name)
        name_edit.setObjectName("step_name")
        self.config_form.addRow("Step Name:", name_edit)

        if isinstance(step, ConversionStep):
            fmt_combo = QComboBox()
            fmt_combo.addItems(["mp4", "mkv", "webm", "gif", "mp3", "wav", "m4a", "flac", "ogg",
                                "jpg", "png", "webp", "heic", "tiff", "pdf", "docx", "odt", "txt", "html"])
            fmt_combo.setCurrentText(step.target_format)
            fmt_combo.setObjectName("target_format")
            self.config_form.addRow("Target Format:", fmt_combo)

            qual_combo = QComboBox()
            qual_combo.addItems(["high", "medium", "low"])
            qual_combo.setCurrentText(step.quality)
            qual_combo.setObjectName("quality")
            self.config_form.addRow("Quality:", qual_combo)

        elif isinstance(step, ExtractAudioStep):
            fmt_combo = QComboBox()
            fmt_combo.addItems(["mp3", "wav", "aac", "m4a", "flac", "ogg", "opus"])
            fmt_combo.setCurrentText(step.audio_format)
            fmt_combo.setObjectName("audio_format")
            self.config_form.addRow("Audio Format:", fmt_combo)

            qual_combo = QComboBox()
            qual_combo.addItems(["high", "medium", "low"])
            qual_combo.setCurrentText(step.audio_quality)
            qual_combo.setObjectName("audio_quality")
            self.config_form.addRow("Quality:", qual_combo)

        elif isinstance(step, NormalizeAudioStep):
            lufs_edit = QLineEdit(str(step.target_lufs))
            lufs_edit.setObjectName("target_lufs")
            self.config_form.addRow("Target LUFS:", lufs_edit)

    def clear_config_form(self):
        # Remove all rows
        while self.config_form.count():
            child = self.config_form.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.current_editing_step = None
        self.apply_config_btn.setEnabled(False)

    def apply_step_config(self):
        if not self.current_editing_step: return

        # Read values from form
        for i in range(self.config_form.rowCount()):
            # Label at itemAt(i, QFormLayout.LabelRole)
            # Field at itemAt(i, QFormLayout.FieldRole)
            field = self.config_form.itemAt(i, QFormLayout.ItemRole.FieldRole).widget()
            if not field: continue

            obj_name = field.objectName()

            if obj_name == "step_name":
                self.current_editing_step.name = field.text()

            elif obj_name == "target_format":
                self.current_editing_step.target_format = field.currentText()
            elif obj_name == "quality":
                self.current_editing_step.quality = field.currentText()

            elif obj_name == "audio_format":
                self.current_editing_step.audio_format = field.currentText()
            elif obj_name == "audio_quality":
                self.current_editing_step.audio_quality = field.currentText()

            elif obj_name == "target_lufs":
                try:
                    self.current_editing_step.target_lufs = float(field.text())
                except ValueError:
                    pass

        self.refresh_steps_list()
        QMessageBox.information(self, "Updated", "Step configuration updated.")

    def move_step_up(self):
        row = self.steps_list.currentRow()
        if row > 0:
            step = self.pipeline.steps.pop(row)
            self.pipeline.steps.insert(row - 1, step)
            self.refresh_steps_list()
            self.steps_list.setCurrentRow(row - 1)

    def move_step_down(self):
        row = self.steps_list.currentRow()
        if row < len(self.pipeline.steps) - 1 and row != -1:
            step = self.pipeline.steps.pop(row)
            self.pipeline.steps.insert(row + 1, step)
            self.refresh_steps_list()
            self.steps_list.setCurrentRow(row + 1)

    def remove_step(self):
        row = self.steps_list.currentRow()
        if row != -1:
            self.pipeline.steps.pop(row)
            self.refresh_steps_list()
            self.clear_config_form()

    def save_pipeline(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a pipeline name")
            return

        self.pipeline.name = name
        valid, msg = self.pipeline.validate()
        if not valid:
            QMessageBox.warning(self, "Error", msg)
            return

        # Save using PresetLibrary
        library = PresetLibrary()
        import re
        filename = re.sub(r'[^a-z0-9_-]+', '_', name.lower()).strip('_') or 'custom_pipeline'
        if library.get_preset(filename) is not None:
            answer = QMessageBox.question(self, "Overwrite?", f"A preset named '{filename}' already exists. Overwrite it?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        success = library.save_preset(self.pipeline, filename)

        if success:
            QMessageBox.information(self, "Success", f"Preset '{name}' saved successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save preset")
