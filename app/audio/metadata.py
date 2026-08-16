import subprocess
from pathlib import Path

from app.audio.ffmpeg import AudioProcessingError, require_ffmpeg


def audio_duration(path: Path) -> float:
    """Read source duration with FFprobe; this is authoritative, not Whisper."""
    require_ffmpeg()
    command = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        duration = float(completed.stdout.strip())
    except ValueError as exc:
        raise AudioProcessingError(
            f"FFprobe could not read duration: {completed.stderr.strip() or 'invalid audio'}"
        ) from exc
    if completed.returncode or duration < 0:
        raise AudioProcessingError("FFprobe failed to read a valid audio duration.")
    return duration
