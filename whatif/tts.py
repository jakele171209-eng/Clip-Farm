"""Voiceover with Kokoro, an open-weight TTS model (Apache-2.0) that runs offline on CPU.

Model files (about 120 MB) come from the kokoro-onnx GitHub releases:
  https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
  kokoro-v1.0.int8.onnx and voices-v1.0.bin -> put them in ./models/
"""
from __future__ import annotations

import os
from functools import lru_cache

import numpy as np

SR = 24000
MODEL_DIR = os.environ.get("WHATIF_MODELS", "models")


@lru_cache(maxsize=1)
def _kokoro():
    from kokoro_onnx import Kokoro

    return Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.int8.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))


def speak(text: str, voice: str = "am_michael", speed: float = 1.05) -> np.ndarray:
    samples, sr = _kokoro().create(text, voice=voice, speed=speed, lang="en-us")
    assert sr == SR, sr
    samples = np.asarray(samples, dtype=np.float32)
    # trim leading/trailing silence so shots cut tight
    loud = np.where(np.abs(samples) > 0.01)[0]
    if len(loud):
        samples = samples[max(0, loud[0] - 600): loud[-1] + 2400]
    return samples
