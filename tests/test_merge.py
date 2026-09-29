from transcriptor.domain import SpeakerInterval, Word
from transcriptor.merge import assign_speakers, group_words, merge_transcript


def test_assignment_uses_greatest_overlap_and_nearest_gap():
    words = [Word(0, 1, "Hello"), Word(1.2, 2, "world"), Word(5, 5.4, "Again")]
    turns = [SpeakerInterval(0, 1.5, "Pessoa A"), SpeakerInterval(1.5, 3, "Pessoa B")]
    result = assign_speakers(words, turns)
    assert [speaker for _, speaker in result] == ["Pessoa A", "Pessoa B", "Pessoa B"]
    assert [word.text for word, _ in result] == ["Hello", "world", "Again"]


def test_grouping_preserves_words_and_splits_speakers():
    assigned = [(Word(0, .4, "Hello"), "Pessoa A"), (Word(.4, .7, ","), "Pessoa A"),
                (Word(.8, 1.2, "there"), "Pessoa A"), (Word(1.3, 2, "Hi"), "Pessoa B")]
    result = group_words(assigned)
    assert [(u.speaker_id, u.text) for u in result] == [("Pessoa A", "Hello, there"), ("Pessoa B", "Hi")]
    assert result[0].start == 0 and result[0].end == 1.2


def test_empty_diarization_keeps_all_text():
    result = merge_transcript([Word(0, 1, "One"), Word(1, 2, "two")], [])
    assert result[0].text == "One two"
