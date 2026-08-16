from pathlib import Path

from app.domain import Word

VALID_MODELS = ("tiny", "base", "small", "medium", "large-v3")
VALID_DEVICES = ("auto", "cpu", "cuda", "mps")


class TranscriptionError(RuntimeError):
    pass


class WhisperTranscriber:
    def __init__(self, model_name: str, device: str, model_dir: Path) -> None:
        if model_name not in VALID_MODELS:
            raise TranscriptionError(f"Unsupported Whisper model '{model_name}'.")
        if device not in VALID_DEVICES:
            raise TranscriptionError(f"Unsupported device '{device}'.")
        self.model_name, self.device, self.model_dir = model_name, device, model_dir

    def transcribe(self, audio_path: Path, language: str | None) -> tuple[list[dict], list[Word]]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise TranscriptionError(
                "faster-whisper is not installed. Install the 'whisper' extra."
            ) from exc
        device = "cpu" if self.device in ("auto", "mps") else self.device
        compute_type = "int8" if device == "cpu" else "float16"
        try:
            model = WhisperModel(
                self.model_name, device=device, compute_type=compute_type,
                download_root=str(self.model_dir),
            )
            segments, _ = model.transcribe(
                str(audio_path), language=language, word_timestamps=True, vad_filter=False
            )
            raw_segments, words = [], []
            for segment in segments:
                raw_segments.append({"start": segment.start, "end": segment.end, "text": segment.text})
                for word in segment.words or []:
                    words.append(Word(word.word.strip(), word.start, word.end))
            return raw_segments, words
        except Exception as exc:
            raise TranscriptionError(f"Whisper transcription failed: {exc}") from exc
