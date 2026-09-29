from transcriptor.domain import Project, Utterance
from transcriptor.projects import load_project, save_project


def test_rename_and_single_reassignment_are_distinct():
    project = Project(utterances=[Utterance(0, 1, "Person A", "one"), Utterance(2, 3, "Person A", "two")])
    project.rename_speaker("Person A", "Bruno")
    assert [project.display_name(u.speaker_id) for u in project.utterances] == ["Bruno", "Bruno"]
    project.reassign_utterance(1, "Person B")
    assert project.utterances[0].speaker_id == "Person A"
    assert project.utterances[1].speaker_id == "Person B"


def test_project_round_trip_preserves_edits(tmp_path):
    project = Project(audio_path="áudio.mp3", model="medium", language="pt", speakers="Auto",
                      utterances=[Utterance(1.2, 3.4, "Person A", "texto corrigido")])
    project.rename_speaker("Person A", "José")
    path = tmp_path / "saved.transcriptor"
    save_project(project, path)
    restored = load_project(path)
    assert restored.utterances[0].text == "texto corrigido"
    assert restored.display_name("Person A") == "José"
    assert restored.dirty is False

