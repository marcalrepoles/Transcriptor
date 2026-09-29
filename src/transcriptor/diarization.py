from __future__ import annotations

from .audio import load_mono_16k
from .domain import SpeakerInterval
from .model_registry import embedding_model_path, segmentation_model_path


def diarize(path: str, speaker_count: int | None = None, progress=None) -> list[SpeakerInterval]:
    import sherpa_onnx
    if progress:
        progress(-1, "Identifying speakers...")
    segmentation = sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
        pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
            model=str(segmentation_model_path())))
    embedding = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(embedding_model_path()))
    clustering = sherpa_onnx.FastClusteringConfig(
        num_clusters=-1 if speaker_count is None else speaker_count, threshold=0.5)
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=segmentation, embedding=embedding, clustering=clustering,
        min_duration_on=0.3, min_duration_off=0.5)
    if hasattr(config, "validate") and not config.validate():
        raise RuntimeError("Speaker diarization model configuration is invalid")
    detector = sherpa_onnx.OfflineSpeakerDiarization(config)
    samples = load_mono_16k(path)

    def report(done: int, total: int) -> int:
        if progress and total:
            progress(int(done * 100 / total), "Identifying speakers...")
        return 0

    result = detector.process(samples, callback=report).sort_by_start_time()
    raw = getattr(result, "segments", result)
    labels: dict[int | str, str] = {}
    intervals: list[SpeakerInterval] = []
    for item in raw:
        label = getattr(item, "speaker", getattr(item, "speaker_id", 0))
        if label not in labels:
            labels[label] = f"Person {chr(65 + len(labels))}"
        intervals.append(SpeakerInterval(float(item.start), float(item.end), labels[label]))
    return intervals
