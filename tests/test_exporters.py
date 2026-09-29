from docx import Document
from transcriptor.domain import Project, Utterance
from transcriptor.exporters import export_docx, export_txt


def sample_project():
    return Project(audio_path="reunião.mp3", utterances=[Utterance(72, 74, "Person A", "Olá, ação e coração.")],
                   speaker_names={"Person A": "João"})


def test_txt_uses_edited_unicode_content(tmp_path):
    path = tmp_path / "out.txt"; export_txt(sample_project(), path)
    assert path.read_text(encoding="utf-8") == "[00:01:12] João: Olá, ação e coração.\n"


def test_docx_contains_edited_content(tmp_path):
    path = tmp_path / "out.docx"; export_docx(sample_project(), path)
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert "João" in text and "Olá, ação e coração." in text

