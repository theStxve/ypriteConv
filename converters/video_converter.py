from .base_converter import BaseConverter, run_tool, short_error, tool_available
from .audio_converter import audio_args
from modules.config_manager import ConfigManager

AUDIO_TARGETS = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'opus', 'wma'}

CRF = {'high': '18', 'medium': '23', 'low': '28'}
AAC_BITRATE = {'high': '192k', 'medium': '128k', 'low': '96k'}


class VideoConverter(BaseConverter):
    def convert(self, source, dest, target_format, **kwargs):
        ffmpeg = ConfigManager().get('ffmpeg_path')
        if not tool_available(ffmpeg):
            return False, f"FFmpeg not found ({ffmpeg}). Set the path in Settings."

        fmt = target_format.lower()
        quality = kwargs.get('quality', 'medium')
        crf = CRF.get(quality, '23')

        if fmt in AUDIO_TARGETS:
            # Video -> audio: extract the soundtrack
            args = ['-vn'] + audio_args(fmt, quality)
        elif fmt == 'gif':
            # Good-looking GIF via generated palette; capped size/fps to keep files sane
            width = {'high': 720, 'medium': 480, 'low': 320}.get(quality, 480)
            fps = {'high': 15, 'medium': 12, 'low': 10}.get(quality, 12)
            vf = (f"fps={fps},scale='min({width},iw)':-1:flags=lanczos,"
                  "split[a][b];[a]palettegen[p];[b][p]paletteuse")
            args = ['-vf', vf, '-loop', '0']
        elif fmt in ('mp4', 'mkv', 'mov', 'm4v'):
            args = ['-c:v', 'libx264', '-crf', crf, '-preset', 'medium',
                    # yuv420p + even dimensions = plays everywhere (browsers, phones, WhatsApp)
                    '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
                    '-c:a', 'aac', '-b:a', AAC_BITRATE.get(quality, '128k')]
            if fmt in ('mp4', 'mov', 'm4v'):
                args += ['-movflags', '+faststart']
        elif fmt == 'webm':
            webm_crf = {'high': '24', 'medium': '32', 'low': '40'}.get(quality, '32')
            args = ['-c:v', 'libvpx-vp9', '-crf', webm_crf, '-b:v', '0', '-row-mt', '1',
                    '-c:a', 'libopus', '-b:a', '128k']
        else:
            # Other containers: let FFmpeg choose suitable defaults
            args = []

        cmd = [ffmpeg, '-y', '-hide_banner', '-i', source] + args + [dest]
        try:
            code, out = run_tool(cmd)
            if code != 0:
                return False, f"FFmpeg Error:\n{short_error(out)}"
            return True, "Success"
        except Exception as e:
            return False, f"Error: {e}"
