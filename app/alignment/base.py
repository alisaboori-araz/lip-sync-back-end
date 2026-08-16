from abc import ABC, abstractmethod
from pathlib import Path

from app.domain import Phoneme, Word


class AlignmentError(RuntimeError):
    pass


class PhonemeAligner(ABC):
    @abstractmethod
    def align(self, audio_path: Path, words: list[Word], language: str) -> list[Phoneme]:
        """Return actual time-aligned phonemes for a normalized WAV."""
