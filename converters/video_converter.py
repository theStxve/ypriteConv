import os

from .base_converter import BaseConverter, run_tool, short_error, tool_available
from .audio_converter import audio_args
from modules.config_manager import ConfigManager

AUDIO_TARGETS = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'opus', 'wma'}

CRF = {'high': '18', 'medium': '23', 'low': '28'}
AAC_BITRATE = {'high': '192k', 'medium': '128k', 'low': '96k'}

ROTATE_FILTERS = {
    'cw': 'transpose=1',
    'ccw': 'transpose=2',
    '180': 'transpose=1,transpose=1',
    'hflip': 'hflip',
    'vflip': 'vflip',
}

# Defaults for the per-file video options (see ui/video_options.py)
DEFAULT_VIDEO_OPTIONS = {
    'rotate': 'none',        # none / cw / ccw / 180 / hflip / vflip
    'height': 0,             # 0 = original, else max height (1080, 720, 480)
    'target_mb': 0,          # 0 = off, else aim for this file size
    'trim_start': None,      # seconds
    'trim_end': None,        # seconds
    'remove_audio': False,
}


def options_active(opts):
    o = {**DEFAULT_VIDEO_OPTIONS, **(opts or {})}
    return o != DEFAULT_VIDEO_OPTIONS


class VideoConverter(BaseConverter):
    def convert(self, source, dest, target_format, **kwargs):
        ffmpeg = ConfigManager().get('ffmpeg_path')
        if not tool_available(ffmpeg):
            return False, f"FFmpeg not found ({ffmpeg}). Set the path in Settings."

        fmt = target_format.lower()
        quality = kwargs.get('quality', 'medium')
        opts = {**DEFAULT_VIDEO_OPTIONS, **(kwargs.get('video_options') or {})}

        # ---- trimming (input seek is fast; we re-encode so it's frame-accurate enough)
        pre_input, post_input = [], []
        start, end = opts['trim_start'], opts['trim_end']
        if start:
            pre_input += ['-ss', f"{start:.3f}"]
        if end and end > (start or 0):
            post_input += ['-t', f"{end - (start or 0):.3f}"]

        # ---- video filters
        vf = []
        if opts['rotate'] in ROTATE_FILTERS:
            vf.append(ROTATE_FILTERS[opts['rotate']])
        if opts['height']:
            vf.append(f"scale=-2:'min({int(opts['height'])},ih)'")

        target_mb = float(opts['target_mb'] or 0)
        if target_mb and fmt not in AUDIO_TARGETS and fmt != 'gif':
            ok, msg = self._encode_to_size(ffmpeg, source, dest, fmt, quality, opts, pre_input,
                                           post_input, vf, target_mb)
            return ok, msg

        args = self._codec_args(fmt, quality, opts, vf)
        return self._run(ffmpeg, pre_input + ['-i', source] + post_input + args, dest)

    # ------------------------------------------------------------------
    def _codec_args(self, fmt, quality, opts, vf, video_kbps=None):
        audio = not opts['remove_audio']
        if fmt in AUDIO_TARGETS:
            return ['-vn'] + audio_args(fmt, quality)

        if fmt == 'gif':
            width = {'high': 720, 'medium': 480, 'low': 320}.get(quality, 480)
            fps = {'high': 15, 'medium': 12, 'low': 10}.get(quality, 12)
            chain = vf + [f"fps={fps}", f"scale='min({width},iw)':-1:flags=lanczos"]
            graph = ",".join(chain) + ",split[a][b];[a]palettegen[p];[b][p]paletteuse"
            return ['-vf', graph, '-loop', '0', '-an']

        if fmt in ('mp4', 'mkv', 'mov', 'm4v'):
            # yuv420p + even dimensions = plays everywhere (browsers, phones, WhatsApp)
            chain = vf + ['scale=trunc(iw/2)*2:trunc(ih/2)*2']
            args = ['-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-vf', ",".join(chain)]
            if video_kbps:
                args += ['-b:v', f"{video_kbps}k", '-maxrate', f"{int(video_kbps * 1.4)}k",
                         '-bufsize', f"{int(video_kbps * 2)}k"]
            else:
                args += ['-crf', CRF.get(quality, '23')]
            args += ['-c:a', 'aac', '-b:a', AAC_BITRATE.get(quality, '128k')] if audio else ['-an']
            if fmt in ('mp4', 'mov', 'm4v'):
                args += ['-movflags', '+faststart']
            return args

        if fmt == 'webm':
            args = ['-c:v', 'libvpx-vp9', '-row-mt', '1', '-deadline', 'good', '-cpu-used', '3']
            if vf:
                args += ['-vf', ",".join(vf)]
            if video_kbps:
                args += ['-b:v', f"{video_kbps}k", '-maxrate', f"{int(video_kbps * 1.4)}k"]
            else:
                args += ['-crf', {'high': '24', 'medium': '32', 'low': '40'}.get(quality, '32'), '-b:v', '0']
            args += ['-c:a', 'libopus', '-b:a', '128k'] if audio else ['-an']
            return args

        # Other containers: FFmpeg defaults plus our filters
        args = ['-vf', ",".join(vf)] if vf else []
        if video_kbps:
            args += ['-b:v', f"{video_kbps}k"]
        if not audio:
            args += ['-an']
        return args

    def _encode_to_size(self, ffmpeg, source, dest, fmt, quality, opts, pre_input, post_input, vf, target_mb):
        from modules.media import duration
        total = duration(source)
        if not total:
            return False, "Can't read the video length, so the target size can't be calculated"
        start, end = opts['trim_start'] or 0, opts['trim_end'] or total
        length = max(0.5, min(end, total) - start)

        audio_kbps = 0 if opts['remove_audio'] else int(AAC_BITRATE.get(quality, '128k')[:-1])
        budget_kbps = target_mb * 8 * 1024 / length * 0.94          # leave room for container overhead
        video_kbps = int(budget_kbps - audio_kbps)
        if video_kbps < 80:
            # Too small for decent video: drop audio quality first
            audio_kbps = 0 if opts['remove_audio'] else 64
            video_kbps = int(budget_kbps - audio_kbps)
        if video_kbps < 50:
            return False, (f"{target_mb:g} MB is too small for {length:.0f} s of video. "
                           "Trim the video or choose a bigger size.")

        target_bytes = target_mb * 1024 * 1024
        msg = ""
        for attempt in range(3):
            args = self._codec_args(fmt, quality, opts, vf, video_kbps)
            if audio_kbps and '-b:a' in args:
                args[args.index('-b:a') + 1] = f"{audio_kbps}k"
            ok, msg = self._run(ffmpeg, pre_input + ['-i', source] + post_input + args, dest)
            if not ok:
                return ok, msg
            size = os.path.getsize(dest)
            if size <= target_bytes:
                return True, f"Success ({size / 1048576:.1f} MB)"
            video_kbps = int(video_kbps * target_bytes / size * 0.93)   # overshot: retry lower
            if video_kbps < 50:
                break
        return True, f"Done, but {os.path.getsize(dest) / 1048576:.1f} MB is above the {target_mb:g} MB target"

    def _run(self, ffmpeg, args, dest):
        try:
            code, out = run_tool([ffmpeg, '-y', '-hide_banner'] + args + [dest])
            if code != 0:
                return False, f"FFmpeg Error:\n{short_error(out)}"
            return True, "Success"
        except Exception as e:
            return False, f"Error: {e}"
