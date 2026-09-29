from transcriptor.model_registry import DIARIZATION_MODELS, WHISPER_MODELS


def test_whisper_registry_mapping():
    assert {key: value.model_id for key, value in WHISPER_MODELS.items()} == {
        "Small": "small", "Medium": "medium", "Large": "large-v3"}


def test_diarization_registry_is_centralized_and_official():
    assert set(DIARIZATION_MODELS) == {"segmentation", "embedding"}
    for model in DIARIZATION_MODELS.values():
        assert model.url.startswith("https://github.com/k2-fsa/sherpa-onnx/releases/download/")
    assert DIARIZATION_MODELS["segmentation"].archive is True

