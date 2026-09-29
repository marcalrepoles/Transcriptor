import sherpa_onnx

from transcriptor.model_registry import embedding_model_path, segmentation_model_path


def test_installed_sherpa_api_accepts_application_configuration():
    segmentation = sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
        pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
            model=str(segmentation_model_path())))
    embedding = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(embedding_model_path()))
    clustering = sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=0.5)
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=segmentation, embedding=embedding, clustering=clustering)
    assert config.clustering.num_clusters == -1
