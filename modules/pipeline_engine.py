"""
Pipeline Execution Engine - Core Components

This module provides the foundation for multi-step conversion pipelines.
"""
import os
import json
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from pathlib import Path


class StepContext:
    """
    Shared context passed between pipeline steps.
    Stores file metadata and intermediate results.
    """
    def __init__(self, source_file: str):
        self.source_file = source_file
        self.current_file = source_file
        self.metadata = {}
        self.intermediate_files = []
        self.step_results = {}
        # Steps write into this temp folder, never next to the user's source file
        self.work_dir = None

    def output_path(self, suffix: str, ext: str) -> str:
        """Path for a step's output file inside the work dir."""
        folder = self.work_dir or str(Path(self.current_file).parent)
        return str(Path(folder) / f"{Path(self.source_file).stem}{suffix}.{ext.lstrip('.')}")
        
    def get_metadata(self, key: str, default=None):
        """Get file metadata"""
        return self.metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any):
        """Set file metadata"""
        self.metadata[key] = value
        
    def add_intermediate_file(self, filepath: str):
        """Track intermediate files for cleanup"""
        self.intermediate_files.append(filepath)
        
    def cleanup_intermediates(self):
        """Remove intermediate files"""
        for filepath in self.intermediate_files:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Warning: Could not remove {filepath}: {e}")


class PipelineStep(ABC):
    """
    Abstract base class for pipeline steps.
    Each step performs one operation on a file.
    """
    def __init__(self, step_id: str, name: str):
        self.step_id = step_id
        self.name = name
        self.config = {}
        
    @abstractmethod
    def execute(self, context: StepContext) -> tuple[bool, str]:
        """
        Execute this step.
        
        Args:
            context: Shared context with file info
            
        Returns:
            (success: bool, message: str)
        """
        pass
    
    def configure(self, **kwargs):
        """Configure step parameters"""
        self.config.update(kwargs)
        
    def to_dict(self) -> Dict:
        """Serialize step to dictionary"""
        return {
            'type': self.__class__.__name__,
            'step_id': self.step_id,
            'name': self.name,
            'config': self.config
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'PipelineStep':
        """Deserialize step from dictionary"""
        # Implemented by step registry
        raise NotImplementedError("Use StepRegistry.create_step()")


class ConditionalBranch:
    """
    Conditional logic for pipeline branching.
    Evaluates conditions and determines next steps.
    """
    def __init__(self, condition_type: str, threshold: Any):
        self.condition_type = condition_type
        self.threshold = threshold
        
    def evaluate(self, context: StepContext) -> bool:
        """
        Evaluate condition against context.
        
        Supported conditions:
        - file_size_gt: File size greater than threshold (bytes)
        - duration_gt: Video/audio duration greater than threshold (seconds)
        - format_is: File format matches threshold
        """
        if self.condition_type == 'file_size_gt':
            size = os.path.getsize(context.current_file)
            return size > int(self.threshold)
            
        elif self.condition_type == 'duration_gt':
            duration = context.get_metadata('duration', 0)
            return duration > float(self.threshold)
            
        elif self.condition_type == 'format_is':
            ext = Path(context.current_file).suffix.lower().lstrip('.')
            return ext == str(self.threshold).lower()
            
        return False


class Pipeline:
    """
    Pipeline orchestrator - manages step execution sequence.
    """
    def __init__(self, name: str = "Unnamed Pipeline"):
        self.name = name
        self.steps: List[PipelineStep] = []
        self.description = ""
        
    def add_step(self, step: PipelineStep):
        """Add a step to the pipeline"""
        self.steps.append(step)
        
    def execute(self, source_file: str, output_file: str) -> tuple[bool, str]:
        """
        Execute the pipeline on a source file.
        
        Args:
            source_file: Input file path
            output_file: Final output file path
            
        Returns:
            (success: bool, message: str)
        """
        from modules.file_detect import EffectiveSource
        with EffectiveSource(source_file) as real_source:
            return self._execute(real_source, output_file)

    def _execute(self, source_file: str, output_file: str) -> tuple[bool, str]:
        import shutil
        import tempfile

        context = StepContext(source_file)
        context.work_dir = tempfile.mkdtemp(prefix="yprite_pipe_")
        self.last_output_file = None

        try:
            # Execute each step in sequence
            for step in self.steps:
                success, message = step.execute(context)
                
                if not success:
                    # Work dir (and with it all partial outputs) is removed in `finally`
                    return False, f"Step '{step.name}' failed: {message}"
                    
                # Store step result
                context.step_results[step.step_id] = {
                    'success': success,
                    'message': message
                }
            
            if context.current_file == source_file:
                return False, "Pipeline produced no output"

            # The real format is decided by the last step -> fix the extension
            final_ext = Path(context.current_file).suffix
            output_file = str(Path(output_file).with_suffix(final_ext))
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            shutil.move(context.current_file, output_file)
            self.last_output_file = output_file

            return True, f"Saved as {os.path.basename(output_file)}"

        except Exception as e:
            return False, f"Pipeline execution error: {str(e)}"
        finally:
            context.cleanup_intermediates()
            shutil.rmtree(context.work_dir, ignore_errors=True)
    
    def to_dict(self) -> Dict:
        """Serialize pipeline to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'steps': [step.to_dict() for step in self.steps]
        }
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate pipeline configuration.
        
        Returns:
            (valid: bool, message: str)
        """
        if not self.steps:
            return False, "Pipeline has no steps"
            
        # Check for duplicate step IDs
        step_ids = [s.step_id for s in self.steps]
        if len(step_ids) != len(set(step_ids)):
            return False, "Duplicate step IDs found"
            
        return True, "Pipeline is valid"
