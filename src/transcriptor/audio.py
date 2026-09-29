from __future__ import annotations

import av
import numpy as np


def audio_duration(path: str) -> float:
    with av.open(path) as container:
        stream = next(s for s in container.streams if s.type == "audio")
        if stream.duration is not None:
            return float(stream.duration * stream.time_base)
        if container.duration:
            return container.duration / av.time_base
    return 0.0


def load_mono_16k(path: str) -> np.ndarray:
    chunks: list[np.ndarray] = []
    with av.open(path) as container:
        stream = next(s for s in container.streams if s.type == "audio")
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
        for frame in container.decode(stream):
            converted = resampler.resample(frame)
            for item in converted if isinstance(converted, list) else [converted]:
                chunks.append(item.to_ndarray().reshape(-1).astype(np.float32))
    return np.concatenate(chunks) if chunks else np.empty(0, dtype=np.float32)

