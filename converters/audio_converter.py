from .base_converter import BaseConverter, run_tool, short_error, tool_available
from modules.config_manager import ConfigManager

# Encoder + whether the format takes a bitrate (lossless formats don't)
AUDIO_CODECS = {
    'mp3':  ('libmp3lame', True),
    'aac':  ('aac', True),
    'm4a':  ('aac', True),
    'ogg':  ('libvorbis', True),
    'opus': ('libopus', True),
    'wma':  ('wmav2', True),
    'amr':  ('libopencore_amrnb', False),
    'wav':  ('pcm_s16le', False),
    'flac': ('flac', False),
}

BITRATES = {'high': '320k', 'medium': '192k', 'low': '96k'}


def audio_args(target_format, quality='medium'):
    """FFmpeg arguments for encoding the audio stream into target_format."""
    codec, uses_bitrate = AUDIO_CODECS.get(target_format.lower(), (None, True))
    args = []
    if codec:
        args += ['-c:a', codec]
    if target_format.lower() == 'amr':
        args += ['-ar', '8000', '-ac', '1']
    elif uses_bitrate:
        bitrate = BITRATES.get(quality, '192k')
        if target_format.lower() == 'opus':
            bitrate = {'high': '192k', 'medium': '128k', 'low': '64k'}.get(quality, '128k')
        args += ['-b:a', bitrate]
    return args


class AudioConverter(BaseConverter):
    def convert(self, source, dest, target_format, **kwargs):
        ffmpeg = ConfigManager().get('ffmpeg_path')
        if not tool_available(ffmpeg):
            return False, f"FFmpeg not found ({ffmpeg}). Set the path in Settings."

        quality = kwargs.get('quality', 'medium')
        # -vn drops embedded cover art that would otherwise break e.g. wav/ogg output
        cmd = [ffmpeg, '-y', '-hide_banner', '-i', source, '-vn', '-map_metadata', '0'] \
            + audio_args(target_format, quality) + [dest]

        try:
            code, out = run_tool(cmd)
            if code != 0:
                return False, f"FFmpeg Error:\n{short_error(out)}"
            return True, "Success"
        except Exception as e:
            return False, f"Error: {e}"
