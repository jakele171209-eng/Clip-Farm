"""Find the moments where chat "roars".

Think of chat as a crowd noise meter. Each second gets a hype score:
messages in that second, plus extra weight for hype emotes and phrases
("KEKW", "W", "CLIP IT"...). We compare each second with the normal noise
level around it, so a big streamer's always-busy chat and a small
streamer's quiet chat are judged fairly. The loudest, clearly-separated
peaks become candidate clips.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, asdict

from .chat import Message

# Weight added per message containing one of these (case-insensitive, whole word).
HYPE_TERMS: dict[str, float] = {
    "kekw": 1.0, "omegalul": 1.0, "lul": 0.6, "lmao": 0.8, "lmfao": 1.0,
    "lol": 0.4, "pog": 0.8, "poggers": 0.8, "pogchamp": 0.8, "w": 0.6,
    "l": 0.5, "clip": 1.5, "clipit": 1.5, "clip it": 1.5, "monkas": 0.8,
    "wtf": 0.8, "omg": 0.6, "no way": 0.8, "holy": 0.6, "ayo": 0.6,
    "icant": 0.8, "aware": 0.4, "😂": 0.8, "💀": 0.8, "🔥": 0.5,
}

_TERM_PATTERNS = [
    (re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE), w)
    for term, w in HYPE_TERMS.items()
]


@dataclass
class Moment:
    peak: float        # second of the loudest point
    start: float       # suggested clip start (seconds)
    end: float         # suggested clip end (seconds)
    score: float       # how far above normal the peak is (higher = bigger)
    messages: int      # chat messages inside the clip window
    top_terms: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def message_weight(text: str) -> float:
    w = 1.0
    for pat, extra in _TERM_PATTERNS:
        if pat.search(text):
            w += extra
    # Spam-caps and repeated emotes are excitement too, but cap it.
    if len(text) >= 4 and text.isupper():
        w += 0.3
    return min(w, 4.0)


def hype_series(messages: list[Message], duration: float | None = None) -> list[float]:
    """Hype score per second."""
    if not messages:
        return []
    n = int(math.ceil(duration if duration else messages[-1].t)) + 1
    series = [0.0] * n
    for m in messages:
        i = int(m.t)
        if 0 <= i < n:
            series[i] += message_weight(m.text)
    return series


def _smooth(xs: list[float], radius: int) -> list[float]:
    if radius <= 0:
        return list(xs)
    out, acc, n = [], 0.0, len(xs)
    prefix = [0.0]
    for x in xs:
        acc += x
        prefix.append(acc)
    for i in range(n):
        lo, hi = max(0, i - radius), min(n, i + radius + 1)
        out.append((prefix[hi] - prefix[lo]) / (hi - lo))
    return out


def _baseline(xs: list[float], window: int) -> tuple[list[float], list[float]]:
    """Rolling mean and std over a wide window (the 'normal noise level')."""
    n = len(xs)
    p1, p2 = [0.0], [0.0]
    for x in xs:
        p1.append(p1[-1] + x)
        p2.append(p2[-1] + x * x)
    means, stds = [], []
    for i in range(n):
        lo, hi = max(0, i - window), min(n, i + window + 1)
        k = hi - lo
        mean = (p1[hi] - p1[lo]) / k
        var = max((p2[hi] - p2[lo]) / k - mean * mean, 0.0)
        means.append(mean)
        stds.append(math.sqrt(var))
    return means, stds


def find_moments(
    messages: list[Message],
    top: int = 10,
    smooth_radius: int = 3,
    baseline_window: int = 300,
    min_gap: float = 60.0,
    pre_roll: float = 20.0,
    post_roll: float = 10.0,
    min_score: float = 2.0,
    duration: float | None = None,
) -> list[Moment]:
    """Return the top chat spikes, loudest first.

    pre_roll: seconds before the peak to start the clip. Chat reacts a few
    seconds AFTER the thing happens, so the action is before the peak.
    """
    series = hype_series(messages, duration)
    if not series:
        return []
    smooth = _smooth(series, smooth_radius)
    means, stds = _baseline(smooth, baseline_window)
    floor = max(0.5, sorted(smooth)[len(smooth) // 2] * 0.5)
    scores = [
        (s - m) / max(sd, floor) for s, m, sd in zip(smooth, means, stds)
    ]

    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    picked: list[int] = []
    for i in order:
        if scores[i] < min_score or len(picked) >= top:
            break
        if all(abs(i - j) >= min_gap for j in picked):
            picked.append(i)

    last = len(series) - 1
    moments = []
    for i in picked:
        start = max(0.0, i - pre_roll)
        end = min(float(last), i + post_roll)
        inside = [m for m in messages if start <= m.t <= end]
        moments.append(Moment(
            peak=float(i), start=start, end=end,
            score=round(scores[i], 2), messages=len(inside),
            top_terms=_top_terms(inside),
        ))
    return moments


def _top_terms(msgs: list[Message], k: int = 5) -> list[str]:
    counts: dict[str, int] = {}
    for m in msgs:
        for term, _ in HYPE_TERMS.items():
            if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", m.text, re.IGNORECASE):
                counts[term] = counts.get(term, 0) + 1
    return [t for t, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:k]]


def fmt_time(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"
