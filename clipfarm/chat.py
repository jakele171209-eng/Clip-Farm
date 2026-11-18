"""Load stream chat replays into a simple list of (seconds, text) messages.

Supported inputs:
- TwitchDownloaderCLI chat JSON (`TwitchDownloaderCLI chatdownload --id <vod> -o chat.json`)
- A generic JSON list: [{"t": 12.5, "text": "KEKW"}, ...]
- CSV with header `t,text`
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Message:
    t: float  # seconds from the start of the stream
    text: str


def load_chat(path: str | Path) -> list[Message]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return _load_csv(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "comments" in data:
        return _from_twitch_downloader(data)
    if isinstance(data, list):
        return sorted(
            (Message(float(m["t"]), str(m.get("text", ""))) for m in data),
            key=lambda m: m.t,
        )
    raise ValueError(f"Unrecognised chat format in {path}")


def _from_twitch_downloader(data: dict) -> list[Message]:
    out = []
    for c in data["comments"]:
        t = c.get("content_offset_seconds")
        if t is None:
            continue
        body = (c.get("message") or {}).get("body", "")
        out.append(Message(float(t), body))
    out.sort(key=lambda m: m.t)
    return out


def _load_csv(path: Path) -> list[Message]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(f)
        msgs = [Message(float(r["t"]), r.get("text", "")) for r in rows]
    msgs.sort(key=lambda m: m.t)
    return msgs
