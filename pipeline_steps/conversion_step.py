"""
Conversion Step - Wraps existing converters as pipeline steps

This step adapts the existing BaseConverter system to work within pipelines.
"""
import os
from pathlib import Path
from modules.pipeline_engine import PipelineStep, StepContext
from modules.format_rules import FormatRules
from converters.doc_converter import DocConverter
from converters.image_converter import ImageConverter
from converters.audio_converter import AudioConverter
from converters.video_converter import VideoConverter


def get_converter(source_ext: str, target_format: str):
    """Pick the converter for a source/target pair (shared by GUI worker and pipelines)."""
    source_ext = source_ext.lower().lstrip('.')
    category = FormatRules.get_category(source_ext)
    if source_ext == 'pdf':
        # PDF -> image uses ImageConverter, PDF -> documents uses DocConverter
        category = 'image' if FormatRules.get_category(target_format) == 'image' else 'document'
    return {
        'document': DocConverter,
        'image': ImageConverter,
        'audio': AudioConverter,
        'video': VideoConverter,
    }.get(category, lambda: None)()


class ConversionStep(PipelineStep):
    """
    Convert file to a target format using existing converters.
    """

    def __init__(self, step_id: str = "convert", name: str = "Convert File"):
        super().__init__(step_id, name)
        self.target_format = None
        self.quality = 'medium'

    def configure(self, target_format: str, quality: str = 'medium', **kwargs):
        """
        Configure conversion parameters.

        Args:
            target_format: Target file format (e.g. 'mp3', 'jpg')
            quality: Quality preset ('high', 'medium', 'low')
        """
        super().configure(**kwargs)
        self.target_format = target_format.lower().lstrip('.')
        self.quality = quality

    def execute(self, context: StepContext) -> tuple[bool, str]:
        """
        Execute file conversion.
        """
        if not self.target_format:
            return False, "No target format configured"

        source = context.current_file
        source_ext = Path(source).suffix.lstrip('.').lower()

        output_file = context.output_path(f"_{self.step_id}_{len(context.step_results)}",
                                          self.target_format)

        converter = get_converter(source_ext, self.target_format)
        if converter is None:
            return False, f"Unsupported format: {source_ext}"

        # Perform conversion
        try:
            success, message = converter.convert(
                source,
                output_file,
                self.target_format,
                quality=self.quality
            )

            if success and not os.path.exists(output_file):
                success, message = False, "Converter reported success but wrote no file"

            if success:
                # Mark old file as intermediate (for cleanup)
                if source != context.source_file:
                    context.add_intermediate_file(source)

                # Update current file to output
                context.current_file = output_file
                context.set_metadata('last_conversion_format', self.target_format)

            return success, message

        except Exception as e:
            return False, f"Conversion error: {str(e)}"

    def to_dict(self):
        """Serialize to dictionary"""
        data = super().to_dict()
        data['config'] = {
            'target_format': self.target_format,
            'quality': self.quality
        }
        return data

    @staticmethod
    def from_dict(data: dict) -> 'ConversionStep':
        """Deserialize from dictionary"""
        step = ConversionStep(
            step_id=data.get('step_id', 'convert'),
            name=data.get('name', 'Convert File')
        )
        config = data.get('config', {})
        if config:
            step.configure(**config)
        return step
