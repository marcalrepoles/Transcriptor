from __future__ import annotations

from .domain import SpeakerInterval, Utterance, Word


def _overlap(start: float, end: float, interval: SpeakerInterval) -> float:
    return max(0.0, min(end, interval.end) - max(start, interval.start))


def assign_speakers(words: list[Word], intervals: list[SpeakerInterval]) -> list[tuple[Word, str]]:
    """Assign each word once, preferring overlap and then nearest interval."""
    if not intervals:
        return [(word, "Person A") for word in words]
    ordered = sorted(intervals, key=lambda item: item.start)
    assigned: list[tuple[Word, str]] = []
    for word in words:
        best = max(ordered, key=lambda item: _overlap(word.start, word.end, item))
        if _overlap(word.start, word.end, best) == 0:
            midpoint = (word.start + word.end) / 2
            best = min(ordered, key=lambda item: min(abs(midpoint - item.start), abs(midpoint - item.end)))
        assigned.append((word, best.speaker_id))
    return assigned


def group_words(assigned: list[tuple[Word, str]], max_gap: float = 1.5) -> list[Utterance]:
    result: list[Utterance] = []
    for word, speaker in assigned:
        text = word.text.strip()
        if not text:
            continue
        if result and result[-1].speaker_id == speaker and word.start - result[-1].end <= max_gap:
            previous = result[-1]
            previous.text = _join_text(previous.text, text)
            previous.end = max(previous.end, word.end)
        else:
            result.append(Utterance(word.start, word.end, speaker, text))
    return result


def _join_text(left: str, right: str) -> str:
    if right[:1] in ",.!?;:%)]}" or left[-1:] in "([{" or right.startswith("'"):
        return left + right
    return left + " " + right


def merge_transcript(words: list[Word], intervals: list[SpeakerInterval]) -> list[Utterance]:
    return group_words(assign_speakers(words, intervals))

