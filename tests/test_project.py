from transcriptor.domain import Project, Utterance
from transcriptor.projects import load_project, save_project


def test_rename_and_single_reassignment_are_distinct():
    project = Project(utterances=[Utterance(0, 1, "Pessoa A", "one"), Utterance(2, 3, "Pessoa A", "two")])
    project.rename_speaker("Pessoa A", "Bruno")
    assert [project.display_name(u.speaker_id) for u in project.utterances] == ["Bruno", "Bruno"]
    project.reassign_utterance(1, "Pessoa B")
    assert project.utterances[0].speaker_id == "Pessoa A"
    assert project.utterances[1].speaker_id == "Pessoa B"


def test_project_round_trip_preserves_edits(tmp_path):
    project = Project(audio_path="áudio.mp3", model="medium", language="pt", speakers="Automático",
                      utterances=[Utterance(1.2, 3.4, "Pessoa A", "texto corrigido")])
    project.rename_speaker("Pessoa A", "José")
    path = tmp_path / "saved.transcriptor"
    save_project(project, path)
    restored = load_project(path)
    assert restored.utterances[0].text == "texto corrigido"
    assert restored.display_name("Pessoa A") == "José"
    assert restored.dirty is False
