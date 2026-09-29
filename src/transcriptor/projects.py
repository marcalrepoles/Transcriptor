from __future__ import annotations

import json
from pathlib import Path

from .domain import Project, Utterance


def save_project(project: Project, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(project.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
    project.project_path = str(target)
    project.dirty = False


def load_project(path: str | Path) -> Project:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("format_version") != 1:
        raise ValueError("Versão do formato de projeto não suportada")
    def translated_speaker(value: str) -> str:
        return "Pessoa " + value[7:] if value.startswith("Person ") else value

    speaker_names = {translated_speaker(key): value for key, value in data.get("speaker_names", {}).items()}
    utterances = [Utterance.from_dict(item) for item in data.get("utterances", [])]
    for utterance in utterances:
        utterance.speaker_id = translated_speaker(utterance.speaker_id)
    project = Project(
        audio_path=data.get("audio_path", ""), model=data.get("model", "small"),
        language=data.get("language"), speakers=str(data.get("speakers", "Automático")).replace("Auto", "Automático"),
        duration=float(data.get("duration", 0)),
        speaker_names=speaker_names,
        utterances=utterances,
        project_path=str(source), dirty=False,
    )
    return project
