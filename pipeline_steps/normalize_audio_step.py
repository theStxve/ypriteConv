"""
Normalize Audio Step - Normalize audio loudness using FFmpeg loudnorm filter
"""
import os
import subprocess
from pathlib import Path
from modules.pipeline_engine import PipelineStep, StepContext
from modules.config_manager import ConfigManager
from converters.base_converter import run_tool, short_error
from converters.audio_converter import audio_args


class NormalizeAudioStep(PipelineStep):
    """
    Normalize audio loudness to target LUFS level.
    Essential for podcast/YouTube audio.
    """

    def __init__(self, step_id: str = "normalize_audio", name: str = "Normalize Audio"):
        super().__init__(step_id, name)
        self.target_lufs = -16.0  # Standard for streaming platforms

    def configure(self, target_lufs: float = -16.0, **kwargs):
        """
        Configure normalization.

        Args:
            target_lufs: Target loudness in LUFS
                         -16 LUFS: Standard (Spotify, YouTube, etc.)
                         -14 LUFS: Louder (Apple Music)
                         -19 LUFS: Quieter (EBU R128)
        """
        super().configure(**kwargs)
        self.target_lufs = float(target_lufs)

    def execute(self, context: StepContext) -> tuple[bool, str]:
        """Normalize audio"""
        config_mgr = ConfigManager()
        ffmpeg = config_mgr.get('ffmpeg_path')

        source = context.current_file
        ext = Path(source).suffix.lstrip('.') or 'wav'
        output_file = context.output_path(f"_normalized_{len(context.step_results)}", ext)

        try:
            # FFmpeg loudnorm filter
            cmd = [
                ffmpeg, '-y', '-i', source,
                '-af', f'loudnorm=I={self.target_lufs}:TP=-1.5:LRA=11',
                '-ar', '48000',  # Sample rate
                '-vn',
            ] + audio_args(ext, 'high') + [output_file]

            code, out = run_tool(cmd)
            if code != 0:
                return False, f"FFmpeg Error:\n{short_error(out)}"

            # Mark old file as intermediate
            if source != context.source_file:
                context.add_intermediate_file(source)

            context.current_file = output_file
            context.set_metadata('audio_normalized', True)
            context.set_metadata('target_lufs', self.target_lufs)

            return True, f"Normalized to {self.target_lufs} LUFS"

        except FileNotFoundError:
            return False, "FFmpeg not found"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def to_dict(self):
        data = super().to_dict()
        data['config'] = {
            'target_lufs': self.target_lufs
        }
        return data
