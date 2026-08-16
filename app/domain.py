from dataclasses import dataclass, field


@dataclass(frozen=True)
class Word:
    word: str
    start: float
    end: float


@dataclass(frozen=True)
class Phoneme:
    phoneme: str
    start: float
    end: float


@dataclass(frozen=True)
class VisemeEvent:
    time: float
    viseme: str


@dataclass
class AnalysisResult:
    duration: float
    interval: float
    events: list[VisemeEvent]
    words: list[Word] = field(default_factory=list)
    phonemes: list[Phoneme] = field(default_factory=list)
