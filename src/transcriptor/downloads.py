from __future__ import annotations

import bz2
import shutil
import tarfile
import urllib.request
from pathlib import Path
from typing import Callable

from .model_registry import DIARIZATION_MODELS, diarization_dir, whisper_path

Progress = Callable[[int, str], None]


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if target != root and root not in target.parents:
            raise ValueError("Unsafe path in model archive")
        if member.issym() or member.islnk():
            raise ValueError("Links are not allowed in model archive")
    archive.extractall(destination, filter="data")


def download_file(url: str, destination: Path, progress: Progress | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=30) as response, partial.open("wb") as output:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                downloaded += len(chunk)
                if progress and total:
                    progress(min(99, int(downloaded * 100 / total)), "Downloading model...")
        partial.replace(destination)
        return destination
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def download_whisper(model_id: str, progress: Progress | None = None) -> Path:
    from faster_whisper import download_model
    target = whisper_path(model_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    if progress:
        progress(0, f"Downloading {model_id}...")
    download_model(model_id, output_dir=str(target))
    if progress:
        progress(100, "Model ready.")
    return target


def download_diarization(progress: Progress | None = None) -> None:
    target_dir = diarization_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    embedding = DIARIZATION_MODELS["embedding"]
    segmentation = DIARIZATION_MODELS["segmentation"]
    if not (target_dir / embedding.filename).exists():
        download_file(embedding.url, target_dir / embedding.filename, progress)
    extracted = target_dir / "sherpa-onnx-pyannote-segmentation-3-0"
    if not extracted.exists():
        archive_path = download_file(segmentation.url, target_dir / segmentation.filename, progress)
        staging = target_dir / ".segmentation-extract"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir()
        try:
            with tarfile.open(archive_path, "r:bz2") as archive:
                _safe_extract(archive, staging)
            roots = [p for p in staging.iterdir() if p.is_dir()]
            source = roots[0] if len(roots) == 1 else staging
            source.replace(extracted)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
            archive_path.unlink(missing_ok=True)
    if progress:
        progress(100, "Speaker models ready.")

