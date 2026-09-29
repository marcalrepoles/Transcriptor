from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class SpeakerInterval:
    start: float
    end: float
    speaker_id: str


@dataclass
class Utterance:
    start: float
    end: float
    speaker_id: str
    text: str

    @classmethod
    def from_dict(cls, value: dict) -> "Utterance":
        return cls(float(value["start"]), float(value["end"]), value["speaker_id"], value["text"])


@dataclass
class Project:
    audio_path: str = ""
    model: str = "small"
    language: str | None = None
    speakers: str = "Automático"
    utterances: list[Utterance] = field(default_factory=list)
    speaker_names: dict[str, str] = field(default_factory=dict)
    duration: float = 0.0
    project_path: str | None = None
    dirty: bool = False

    def display_name(self, speaker_id: str) -> str:
        return self.speaker_names.get(speaker_id, speaker_id)

    def rename_speaker(self, speaker_id: str, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            self.speaker_names.pop(speaker_id, None)
        else:
            self.speaker_names[speaker_id] = cleaned
        self.dirty = True

    def reassign_utterance(self, index: int, speaker_id: str) -> None:
        self.utterances[index].speaker_id = speaker_id
        self.dirty = True

    def to_dict(self) -> dict:
        return {
            "format_version": 1,
            "audio_path": self.audio_path,
            "model": self.model,
            "language": self.language,
            "speakers": self.speakers,
            "duration": self.duration,
            "speaker_names": self.speaker_names,
            "utterances": [asdict(item) for item in self.utterances],
        }

    @property
    def audio_name(self) -> str:
        return Path(self.audio_path).name if self.audio_path else "Transcrição"
