"""Make short, punchy caption files with Whisper (runs locally, free).

Needs `pip install faster-whisper`. Captions are split into chunks of a few
words so they pop on screen like typical Shorts captions.
"""
from __future__ import annotations

from pathlib import Path


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def words_to_srt(words: list[tuple[float, float, str]], max_words: int = 3) -> str:
    """words: (start, end, word) relative to the clip start."""
    lines, idx = [], 1
    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]
        text = " ".join(w.strip() for _, _, w in chunk).upper()
        lines.append(f"{idx}\n{_ts(chunk[0][0])} --> {_ts(chunk[-1][1])}\n{text}\n")
        idx += 1
    return "\n".join(lines)


def transcribe_to_srt(clip_audio: str, out_srt: str, model_size: str = "small") -> Path:
    from faster_whisper import WhisperModel  # optional dependency

    model = WhisperModel(model_size, compute_type="int8")
    segments, _ = model.transcribe(clip_audio, word_timestamps=True)
    words = [(w.start, w.end, w.word) for seg in segments for w in (seg.words or [])]
    Path(out_srt).write_text(words_to_srt(words), encoding="utf-8")
    return Path(out_srt)
