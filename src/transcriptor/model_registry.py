from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import MODEL_DIR


@dataclass(frozen=True)
class WhisperModel:
    label: str
    model_id: str


@dataclass(frozen=True)
class DiarizationModel:
    key: str
    filename: str
    url: str
    archive: bool = False


WHISPER_MODELS = {
    "Small": WhisperModel("Small", "small"),
    "Medium": WhisperModel("Medium", "medium"),
    "Large": WhisperModel("Large", "large-v3"),
}

# Official, unauthenticated sherpa-onnx release assets. Kept here so upgrades are localized.
SHERPA_RELEASE = "v1.12.20"
SHERPA_BASE = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models"
DIARIZATION_MODELS = {
    "segmentation": DiarizationModel(
        "segmentation", "sherpa-onnx-pyannote-segmentation-3-0.tar.bz2",
        f"{SHERPA_BASE}/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2", True),
    "embedding": DiarizationModel(
        "embedding", "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx",
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"),
}


def whisper_path(model_id: str) -> Path:
    return MODEL_DIR / "whisper" / model_id


def diarization_dir() -> Path:
    return MODEL_DIR / "diarization"


def segmentation_model_path() -> Path:
    base = diarization_dir() / "sherpa-onnx-pyannote-segmentation-3-0"
    candidates = (base / "model.onnx", base / "model.int8.onnx")
    return next((p for p in candidates if p.exists()), candidates[0])


def embedding_model_path() -> Path:
    return diarization_dir() / DIARIZATION_MODELS["embedding"].filename


def whisper_installed(model_id: str) -> bool:
    path = whisper_path(model_id)
    return path.is_dir() and any(path.iterdir())


def diarization_installed() -> bool:
    return segmentation_model_path().is_file() and embedding_model_path().is_file()

