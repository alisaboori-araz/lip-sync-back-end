import math

from app.domain import Phoneme, VisemeEvent
from app.visemes.mapper import VisemeMapper


def generate_timeline(
    duration: float, interval: float, phonemes: list[Phoneme], mapper: VisemeMapper
) -> list[VisemeEvent]:
    if duration < 0 or interval <= 0:
        raise ValueError("Duration must be non-negative and interval must be positive.")
    frame_count = math.ceil(duration / interval)
    ordered = sorted(phonemes, key=lambda phone: phone.start)
    result, phone_index = [], 0
    for frame_index in range(frame_count):
        time = round(frame_index * interval, 8)
        while phone_index < len(ordered) and ordered[phone_index].end <= time:
            phone_index += 1
        active = (
            ordered[phone_index]
            if phone_index < len(ordered)
            and ordered[phone_index].start <= time < ordered[phone_index].end
            else None
        )
        viseme = mapper.map(active.phoneme) if active else "sil"
        if not result or result[-1].viseme != viseme:
            result.append(VisemeEvent(time=time, viseme=viseme))
    return result
