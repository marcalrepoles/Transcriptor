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
        raise ValueError("Unsupported project format version")
    project = Project(
        audio_path=data.get("audio_path", ""), model=data.get("model", "small"),
        language=data.get("language"), speakers=str(data.get("speakers", "Auto")),
        duration=float(data.get("duration", 0)),
        speaker_names=dict(data.get("speaker_names", {})),
        utterances=[Utterance.from_dict(item) for item in data.get("utterances", [])],
        project_path=str(source), dirty=False,
    )
    return project

