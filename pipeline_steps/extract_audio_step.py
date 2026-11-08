"""
Extract Audio Step - Extract audio track from video files
"""
import os
import subprocess
from pathlib import Path
from modules.pipeline_engine import PipelineStep, StepContext
from modules.config_manager import ConfigManager
from converters.base_converter import run_tool, short_error
from converters.audio_converter import audio_args


class ExtractAudioStep(PipelineStep):
    """
    Extract audio from video file.
    Useful for Video → Audio pipelines.
    """

    def __init__(self, step_id: str = "extract_audio", name: str = "Extract Audio"):
        super().__init__(step_id, name)
        self.audio_format = 'mp3'
        self.audio_quality = 'medium'

    def configure(self, audio_format: str = 'mp3', audio_quality: str = 'medium', **kwargs):
        """
        Configure audio extraction.

        Args:
            audio_format: Output audio format (mp3, wav, aac, etc.)
            audio_quality: Quality preset ('high', 'medium', 'low')
        """
        super().configure(**kwargs)
        self.audio_format = audio_format.lower()
        self.audio_quality = audio_quality

    def execute(self, context: StepContext) -> tuple[bool, str]:
        """Extract audio track"""
        config_mgr = ConfigManager()
        ffmpeg = config_mgr.get('ffmpeg_path')

        source = context.current_file
        output_file = context.output_path(f"_audio_{len(context.step_results)}", self.audio_format)

        try:
            cmd = [ffmpeg, '-y', '-hide_banner', '-i', source, '-vn'] \
                + audio_args(self.audio_format, self.audio_quality) + [output_file]
            code, out = run_tool(cmd)
            if code != 0:
                if 'does not contain any stream' in out or 'matches no streams' in out:
                    return False, "File has no audio track"
                return False, f"FFmpeg Error:\n{short_error(out)}"

            # Mark old file as intermediate
            if source != context.source_file:
                context.add_intermediate_file(source)

            context.current_file = output_file
            context.set_metadata('audio_extracted', True)

            return True, f"Extracted audio as {self.audio_format}"

        except FileNotFoundError:
            return False, "FFmpeg not found"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def to_dict(self):
        data = super().to_dict()
        data['config'] = {
            'audio_format': self.audio_format,
            'audio_quality': self.audio_quality
        }
        return data
