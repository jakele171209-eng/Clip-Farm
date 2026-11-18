import json
import random
import shutil
import subprocess

import pytest

from clipfarm.chat import Message, load_chat
from clipfarm.spikes import find_moments, message_weight
from clipfarm.captions import words_to_srt
from clipfarm.cut import build_cut_command, cut_clip


def fake_stream(seconds=3600, spikes=(900, 2400), seed=1):
    """Quiet chat (~2 msg/s) with bursts of KEKW / CLIP IT at the spike times."""
    rng = random.Random(seed)
    msgs = []
    for s in range(seconds):
        for _ in range(rng.randint(0, 4)):
            msgs.append(Message(s + rng.random(), rng.choice(["hi", "nice", "gg", "what game is this"])))
    for peak in spikes:
        for s in range(peak, peak + 8):
            for _ in range(40):
                msgs.append(Message(s + rng.random(), rng.choice(["KEKW", "CLIP IT", "OMEGALUL", "W"])))
    msgs.sort(key=lambda m: m.t)
    return msgs


def test_weight_counts_hype_terms():
    assert message_weight("hello") == 1.0
    assert message_weight("KEKW") > 1.5
    assert message_weight("clip it") > 2.0
    assert message_weight("well") == 1.0  # 'w' must be a whole word


def test_finds_the_planted_spikes():
    moments = find_moments(fake_stream(), top=5)
    peaks = sorted(m.peak for m in moments[:2])
    assert abs(peaks[0] - 904) <= 10
    assert abs(peaks[1] - 2404) <= 10
    # clip starts before the peak because chat reacts after the action
    assert all(m.start < m.peak < m.end for m in moments)
    assert "kekw" in moments[0].top_terms or "clip it" in moments[0].top_terms


def test_quiet_stream_gives_nothing():
    assert find_moments(fake_stream(spikes=()), top=5, min_score=4.0) == []


def test_loads_twitch_downloader_json(tmp_path):
    p = tmp_path / "chat.json"
    p.write_text(json.dumps({"comments": [
        {"content_offset_seconds": 5.2, "message": {"body": "W"}},
        {"content_offset_seconds": 1.0, "message": {"body": "hi"}},
    ]}))
    msgs = load_chat(p)
    assert [m.text for m in msgs] == ["hi", "W"]


def test_srt_chunks_words():
    srt = words_to_srt([(0, 0.4, "no"), (0.4, 0.8, "way"), (0.8, 1.2, "he"), (1.2, 1.6, "did")])
    assert "NO WAY HE" in srt and "DID" in srt and "00:00:01,200 --> 00:00:01,600" in srt


def test_cut_command_rejects_bad_range():
    with pytest.raises(ValueError):
        build_cut_command("v.mp4", 10, 5, "o.mp4")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_cut_makes_vertical_clip_with_captions(tmp_path):
    src = tmp_path / "vod.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "12",
                    "-c:v", "libx264", "-c:a", "aac", str(src)], check=True, capture_output=True)
    srt = tmp_path / "c.srt"
    srt.write_text(words_to_srt([(0.0, 1.0, "test"), (1.0, 2.0, "caption")]))
    out = cut_clip(str(src), 2, 7, str(tmp_path / "clip.mp4"), str(srt))
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:format=duration", "-of", "json", str(out)],
                           capture_output=True, text=True, check=True)
    info = json.loads(probe.stdout)
    assert (info["streams"][0]["width"], info["streams"][0]["height"]) == (1080, 1920)
    assert 4.5 <= float(info["format"]["duration"]) <= 5.5
