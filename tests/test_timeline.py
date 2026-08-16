import pytest

from app.domain import Phoneme
from app.timeline.generator import generate_timeline
from app.visemes.mapper import VisemeMapper


def test_timeline_covers_full_duration_with_silence():
    events = generate_timeline(10.0, 0.04, [], VisemeMapper())
    assert len(events) == 1
    assert events[0].time == 0
    assert {event.viseme for event in events} == {"sil"}


def test_timeline_preserves_silence_before_and_after_speech():
    events = generate_timeline(1.0, 0.04, [Phoneme("p", 0.4, 0.5)], VisemeMapper())
    assert [(event.time, event.viseme) for event in events] == [
        (0.0, "sil"),
        (0.4, "PP"),
        (0.52, "sil"),
    ]


def test_timeline_uses_frame_indexes_for_spacing():
    events = generate_timeline(0.13, 0.04, [], VisemeMapper())
    assert [event.time for event in events] == [0.0]


def test_timeline_merges_consecutive_identical_visemes():
    events = generate_timeline(
        0.2,
        0.04,
        [Phoneme("p", 0.04, 0.12), Phoneme("b", 0.12, 0.2)],
        VisemeMapper(),
    )
    assert [(event.time, event.viseme) for event in events] == [
        (0.0, "sil"),
        (0.04, "PP"),
    ]


@pytest.mark.parametrize(
    ("phoneme", "viseme"),
    [("p", "PP"), ("θ", "TH"), ("AA1", "AA"), ("unknown", "sil")],
)
def test_mapping(phoneme, viseme):
    assert VisemeMapper().map(phoneme) == viseme


@pytest.mark.parametrize(
    ("phoneme", "viseme"),
    [("p", "PP"), ("ʃ", "SH"), ("tʃ", "CH"), ("ɒ", "AA"), ("unknown", "sil")],
)
def test_persian_mapping(phoneme, viseme):
    assert VisemeMapper("fa").map(phoneme) == viseme
