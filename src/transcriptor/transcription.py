from __future__ import annotations

import logging

from .domain import Word
from .model_registry import whisper_path

log = logging.getLogger(__name__)


def _load_model(model_id: str):
    from faster_whisper import WhisperModel
    path = str(whisper_path(model_id))
    try:
        return WhisperModel(path, device="cuda", compute_type="float16"), "NVIDIA GPU"
    except Exception as error:
        log.info("CUDA unavailable, falling back to CPU: %s", error)
        return WhisperModel(path, device="cpu", compute_type="int8"), "CPU"


def _transcribe_with_model(model, path: str, progress=None) -> tuple[list[Word], str | None]:
    segments, info = model.transcribe(path, word_timestamps=True, vad_filter=True)
    words: list[Word] = []
    for segment in segments:
        if segment.words:
            words.extend(Word(float(w.start), float(w.end), w.word) for w in segment.words)
        else:
            words.append(Word(float(segment.start), float(segment.end), segment.text))
        if progress:
            progress(-1, "Transcrevendo...")
    return words, getattr(info, "language", None)


def transcribe(path: str, model_id: str, progress=None) -> tuple[list[Word], str | None, str]:
    model, hardware = _load_model(model_id)
    try:
        words, language = _transcribe_with_model(model, path, progress)
    except Exception as error:
        if hardware != "NVIDIA GPU":
            raise
        log.warning("CUDA inference failed, retrying on CPU: %s", error)
        from faster_whisper import WhisperModel
        model = WhisperModel(str(whisper_path(model_id)), device="cpu", compute_type="int8")
        hardware = "CPU"
        words, language = _transcribe_with_model(model, path, progress)
    return words, language, hardware
