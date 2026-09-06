"""Lossless, optional playback indexing for fully finalized recorder takes.

Original segments are never modified. The project-bundled FFmpeg is used rather
than a global Homebrew executable. Failure leaves raw playback available.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import uuid


def ffmpeg_executable():
    import imageio_ffmpeg
    # Do not fall back to PATH/Homebrew, including an unrelated environment
    # override. Runtime playback uses only the installed wheel's own binary.
    bundled = Path(imageio_ffmpeg.__file__).resolve().parent / 'binaries'
    for candidate in sorted(bundled.glob('ffmpeg*')):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise OSError('The project-bundled FFmpeg binary is unavailable.')


def probe_duration(path, executable=None):
    try:
        result = subprocess.run([executable or ffmpeg_executable(), '-nostdin', '-hide_banner', '-i', str(path)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=15)
        match = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', result.stderr)
        if not match:
            return None
        hours, minutes, seconds = map(float, match.groups())
        value = hours * 3600 + minutes * 60 + seconds
        return value if math.isfinite(value) and value > 0 else None
    except (OSError, subprocess.SubprocessError, ImportError):
        return None


def indexed_take(storage_directory, take_id, rows, final):
    """Return {path, durationSeconds, signature}, or None for unindexed/raw data."""
    if not final or final['expected_count'] <= 0 or [row['chunk_index'] for row in rows] != list(range(final['expected_count'])):
        return None
    mime = rows[0]['mime_type'] if rows else None
    formats = {'audio/webm': ('.webm', []), 'audio/mp4': ('.m4a', ['-movflags', '+faststart']), 'audio/ogg': ('.ogg', [])}
    if mime not in formats or sum(row['size'] for row in rows) > 256 * 1024 * 1024:
        return None
    directory = Path(storage_directory).resolve()
    signature = hashlib.sha256(json.dumps({'version': 'lossless-index-v1', 'segments': [row['sha256'] for row in rows],
        'count': final['expected_count'], 'mimeType': mime}, sort_keys=True).encode()).hexdigest()
    suffix, extra = formats[mime]
    cache = directory / 'playback'
    temporary_input = temporary_output = temporary_metadata = None
    try:
        cache.mkdir(mode=0o700, exist_ok=True)
        if cache.is_symlink() or not cache.resolve().is_relative_to(directory):
            return None
        target = cache / f'{take_id}-{signature}{suffix}'
        metadata_path = target.with_suffix(target.suffix + '.json')
        if target.is_symlink() or metadata_path.is_symlink():
            return None
        if target.is_file() and metadata_path.is_file():
            metadata = json.loads(metadata_path.read_text())
            duration = metadata.get('durationSeconds')
            if metadata.get('signature') == signature and isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0 and target.stat().st_size > 0:
                return {'path': target, **metadata}
        token = uuid.uuid4().hex
        temporary_input = cache / f'.{token}.input{suffix}'
        temporary_output = cache / f'.{token}.indexed{suffix}'
        temporary_metadata = cache / f'.{token}.json'
        with temporary_input.open('xb') as destination:
            for row in rows:
                source = (directory / row['relative_path']).resolve()
                if not source.is_relative_to(directory) or not source.is_file():
                    return None
                with source.open('rb') as fragment:
                    shutil.copyfileobj(fragment, destination)
        executable = ffmpeg_executable()
        result = subprocess.run([executable, '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                                 '-i', str(temporary_input), '-map', '0:a:0', '-c', 'copy', *extra, str(temporary_output)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
        if result.returncode != 0 or not temporary_output.is_file() or temporary_output.stat().st_size == 0:
            return None
        duration = probe_duration(temporary_output, executable)
        if duration is None:
            return None
        metadata = {'signature': signature, 'durationSeconds': duration, 'method': 'lossless-remux', 'codecReencoded': False}
        temporary_metadata.write_text(json.dumps(metadata))
        os.replace(temporary_output, target)
        os.replace(temporary_metadata, metadata_path)
        return {'path': target, **metadata}
    except (OSError, ValueError, ImportError, subprocess.SubprocessError):
        return None
    finally:
        for path in [temporary_input, temporary_output, temporary_metadata]:
            if path is not None:
                path.unlink(missing_ok=True)
