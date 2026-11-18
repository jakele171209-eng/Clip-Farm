"""Command line entry point.

  python -m clipfarm find --chat chat.json --top 10 --out moments.json
  python -m clipfarm cut  --video vod.mp4 --moments moments.json --outdir clips/ [--captions]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .chat import load_chat
from .spikes import find_moments, fmt_time


def cmd_find(a: argparse.Namespace) -> int:
    msgs = load_chat(a.chat)
    moments = find_moments(msgs, top=a.top, pre_roll=a.pre, post_roll=a.post,
                           min_gap=a.gap, min_score=a.min_score)
    print(f"{len(msgs)} chat messages, {len(moments)} moments found\n")
    for n, m in enumerate(moments, 1):
        print(f"{n:>2}. {fmt_time(m.start)} to {fmt_time(m.end)}  score {m.score:>5}  "
              f"msgs {m.messages:>4}  {', '.join(m.top_terms)}")
    if a.out:
        Path(a.out).write_text(json.dumps([m.to_dict() for m in moments], indent=2))
        print(f"\nSaved to {a.out}")
    return 0


def cmd_cut(a: argparse.Namespace) -> int:
    from .cut import cut_clip

    moments = json.loads(Path(a.moments).read_text())
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for n, m in enumerate(moments, 1):
        out = outdir / f"clip_{n:02d}.mp4"
        srt = None
        if a.captions:
            from .captions import transcribe_to_srt
            raw = outdir / f"clip_{n:02d}_raw.mp4"
            cut_clip(a.video, m["start"], m["end"], str(raw))
            srt = str(transcribe_to_srt(str(raw), str(outdir / f"clip_{n:02d}.srt")))
        cut_clip(a.video, m["start"], m["end"], str(out), srt)
        print(f"wrote {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="clipfarm")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("find", help="find chat spikes")
    f.add_argument("--chat", required=True)
    f.add_argument("--top", type=int, default=10)
    f.add_argument("--pre", type=float, default=20.0, help="seconds before the peak")
    f.add_argument("--post", type=float, default=10.0, help="seconds after the peak")
    f.add_argument("--gap", type=float, default=60.0, help="min seconds between clips")
    f.add_argument("--min-score", type=float, default=2.0)
    f.add_argument("--out")
    f.set_defaults(func=cmd_find)

    c = sub.add_parser("cut", help="cut vertical clips")
    c.add_argument("--video", required=True)
    c.add_argument("--moments", required=True)
    c.add_argument("--outdir", default="clips")
    c.add_argument("--captions", action="store_true", help="burn in Whisper captions")
    c.set_defaults(func=cmd_cut)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
