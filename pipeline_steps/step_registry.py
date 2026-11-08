"""
Step Registry - Factory for creating pipeline steps from configuration
"""
from typing import Dict, Type
from modules.pipeline_engine import PipelineStep
from .conversion_step import ConversionStep
from .extract_audio_step import ExtractAudioStep
from .normalize_audio_step import NormalizeAudioStep


class StepRegistry:
    """
    Registry for all available pipeline step types.
    Provides factory method to create steps from serialized data.
    """
    
    _steps: Dict[str, Type[PipelineStep]] = {
        'ConversionStep': ConversionStep,
        'ExtractAudioStep': ExtractAudioStep,
        'NormalizeAudioStep': NormalizeAudioStep,
    }
    
    @classmethod
    def register_step(cls, step_class: Type[PipelineStep]):
        """Register a new step type"""
        cls._steps[step_class.__name__] = step_class
        
    @classmethod
    def create_step(cls, step_data: Dict) -> PipelineStep:
        """
        Create a step instance from serialized data.
        
        Args:
            step_data: Dictionary with 'type', 'step_id', 'name', 'config'
            
        Returns:
            PipelineStep instance
            
        Raises:
            ValueError: If step type not found
        """
        step_type = step_data.get('type')
        
        if step_type not in cls._steps:
            raise ValueError(f"Unknown step type: {step_type}")
        
        step_class = cls._steps[step_type]
        
        # Create instance
        step = step_class(
            step_id=step_data.get('step_id', 'step'),
            name=step_data.get('name', 'Unnamed Step')
        )
        
        # Configure with saved config
        config = step_data.get('config', {})
        if config:
            step.configure(**config)
        
        return step
    
    @classmethod
    def get_available_steps(cls) -> list:
        """Get list of all available step types"""
        return list(cls._steps.keys())
    
    @classmethod
    def get_step_info(cls, step_type: str) -> Dict:
        """Get metadata about a step type"""
        if step_type not in cls._steps:
            return {}
        
        step_class = cls._steps[step_type]
        return {
            'type': step_type,
            'name': step_class.__name__,
            'description': step_class.__doc__ or ''
        }
