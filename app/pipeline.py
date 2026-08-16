from pathlib import Path

from app.alignment.base import PhonemeAligner
from app.audio.ffmpeg import normalize_audio
from app.audio.metadata import audio_duration
from app.domain import AnalysisResult
from app.timeline.generator import generate_timeline
from app.transcription.whisper import WhisperTranscriber
from app.visemes.mapper import VisemeMapper


class AnalysisPipeline:
    def __init__(self, transcriber: WhisperTranscriber, aligner: PhonemeAligner) -> None:
        self.transcriber, self.aligner = transcriber, aligner

    def run(self, source: Path, normalized: Path, language: str, interval: float, on_stage=None) -> AnalysisResult:
        notify = on_stage or (lambda _: None)
        notify("preparing_audio")
        duration = audio_duration(source)
        normalize_audio(source, normalized)
        notify("transcribing")
        _, words = self.transcriber.transcribe(normalized, language)
        notify("aligning")
        phonemes = self.aligner.align(normalized, words, language)
        notify("mapping")
        mapper = VisemeMapper(language)
        notify("generating_timeline")
        events = generate_timeline(duration, interval, phonemes, mapper)
        return AnalysisResult(duration, interval, events, words, phonemes)
