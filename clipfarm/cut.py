"""Cut a moment out of a stream recording as a vertical 9:16 Short.

Layout: the full 16:9 frame sits in the middle over a blurred, zoomed copy
of itself, so nothing is cropped away (works for any streamer layout).
Captions from an .srt file are burned in, big and centred, near the bottom.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

W, H = 1080, 1920


def _escape_filter_path(p: str) -> str:
    # ffmpeg filter args need ':' and '\\' and "'" escaped.
    return p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_cut_command(
    video: str, start: float, end: float, out: str, srt: str | None = None,
) -> list[str]:
    if end <= start:
        raise ValueError("end must be after start")
    graph = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2[bgb];"
        f"[fg]scale={W}:-2[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2"
    )
    if srt:
        style = ("FontName=Arial,FontSize=16,Bold=1,PrimaryColour=&H00FFFFFF,"
                 "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,"
                 "Alignment=2,MarginV=60")
        graph += f",subtitles='{_escape_filter_path(srt)}':force_style='{style}'"
    graph += "[v]"
    return [
        "ffmpeg", "-y", "-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", video,
        "-filter_complex", graph, "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out,
    ]


def cut_clip(video: str, start: float, end: float, out: str, srt: str | None = None) -> Path:
    cmd = build_cut_command(video, start, end, out, srt)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {shlex.join(cmd)}\n{proc.stderr[-2000:]}")
    return Path(out)
