import shutil
import subprocess
from pathlib import Path


class AudioProcessingError(RuntimeError):
    pass


def require_ffmpeg() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise AudioProcessingError(
            f"Missing required executable(s): {', '.join(missing)}. Install FFmpeg and add it to PATH."
        )


def normalize_audio(source: Path, destination: Path) -> None:
    require_ffmpeg()
    command = [
        "ffmpeg", "-y", "-v", "error", "-i", str(source),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise AudioProcessingError(f"FFmpeg could not normalize audio: {completed.stderr.strip()}")
