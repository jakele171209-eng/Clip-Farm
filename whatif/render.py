"""Turn a story JSON into a vertical 9:16 MP4 with voice, captions, labels and music."""
from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw

from . import art
from .art import H, W
from .tts import SR, speak

FPS = 30
GAP = 0.22  # seconds of air between shots


@dataclass
class Shot:
    spec: dict
    start: float = 0.0
    dur: float = 0.0
    words: list = field(default_factory=list)  # (word, t0, t1) relative to shot start


# ------------------------------------------------------------------ timing

def word_times(text: str, dur: float):
    """Spread words over the spoken duration, weighting by length and punctuation pauses."""
    words = text.split()
    weights = []
    for w in words:
        wt = len(re.sub(r"[^\w]", "", w)) + 2
        if w.endswith((".", "?", "!")):
            wt += 6
        elif w.endswith((",", ";", ":")):
            wt += 3
        weights.append(wt)
    total = sum(weights) or 1
    t, out = 0.0, []
    for w, wt in zip(words, weights):
        d = dur * wt / total
        out.append((w, t, t + d))
        t += d
    return out


def chunks(words, max_words=3, max_chars=15):
    """Group words into caption chunks, breaking at punctuation or when a chunk gets long."""
    out, cur = [], []
    for i, item in enumerate(words):
        cur.append(item)
        nxt = words[i + 1][0] if i + 1 < len(words) else ""
        long = len(" ".join(w[0] for w in cur)) + 1 + len(nxt) > max_chars
        if len(cur) >= max_words or long or item[0].endswith((".", "?", "!", ",")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


# ------------------------------------------------------------------ audio

def music_bed(seconds: float) -> np.ndarray:
    """Original ambient pad + soft plucks, generated from sine waves (no licensing needed)."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G
    bar = 4.0
    for ci in range(int(seconds / bar) + 1):
        notes = chords[ci % len(chords)]
        s0, s1 = int(ci * bar * SR), min(n, int((ci + 1) * bar * SR) + SR // 2)
        if s0 >= n:
            break
        tt = t[s0:s1] - ci * bar
        env = np.minimum(1, tt / 0.8) * np.minimum(1, np.maximum(0, (bar + 0.5 - tt) / 0.8))
        for m in notes:
            f = 440 * 2 ** ((m - 69) / 12)
            out[s0:s1] += (0.5 * np.sin(2 * np.pi * f * tt) + 0.15 * np.sin(4 * np.pi * f * tt)) * env * 0.06
        for k, m in enumerate(notes * 2):  # arpeggio plucks
            st = k * bar / 6
            p0 = s0 + int(st * SR)
            p1 = min(n, p0 + int(0.6 * SR))
            if p0 >= n:
                continue
            pt = np.arange(p1 - p0) / SR
            f = 440 * 2 ** ((m + 12 - 69) / 12)
            out[p0:p1] += np.sin(2 * np.pi * f * pt) * np.exp(-pt * 7) * 0.05
    return out


def pop(at: float, buf: np.ndarray, pitch: float = 880):
    i0 = int(at * SR)
    m = int(0.09 * SR)
    if i0 + m > len(buf):
        return
    pt = np.arange(m) / SR
    f = pitch * (1 + 0.8 * np.exp(-pt * 40))
    buf[i0:i0 + m] += np.sin(2 * np.pi * f * pt) * np.exp(-pt * 45) * 0.25


def boom(at: float, buf: np.ndarray):
    """Low thump + noise crack for impacts."""
    i0 = int(at * SR)
    m = int(0.5 * SR)
    if i0 + m > len(buf):
        m = len(buf) - i0
    if m <= 0:
        return
    pt = np.arange(m) / SR
    rng = np.random.default_rng(1)
    noise = rng.standard_normal(m) * np.exp(-pt * 30)
    thump = np.sin(2 * np.pi * (60 + 90 * np.exp(-pt * 20)) * pt) * np.exp(-pt * 6)
    buf[i0:i0 + m] += (thump * 0.7 + noise * 0.35)


def whoosh(at: float, buf: np.ndarray):
    i0 = int(at * SR)
    m = int(0.22 * SR)
    if i0 + m > len(buf) or i0 < 0:
        return
    pt = np.arange(m) / SR
    rng = np.random.default_rng(2)
    noise = np.convolve(rng.standard_normal(m), np.ones(12) / 12, mode="same")
    env = np.sin(np.pi * pt / pt[-1]) ** 2
    buf[i0:i0 + m] += noise * env * 0.18


def impact_time(shot) -> float | None:
    imp = shot.spec.get("impact")
    if not imp:
        return None
    key = imp.get("word", "").lower()
    for w, t0, t1 in shot.words:
        if key and re.sub(r"[^\w]", "", w.lower()) == key:
            return t0
    return shot.dur * imp.get("at", 0.5)


def write_wav(path, samples):
    s = np.clip(samples, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((s * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------ drawing

def ease_pop(x: float) -> float:
    """0..1 -> scale with a small overshoot."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return 1 + 2.2 * (x - 1) ** 3 + 1.2 * (x - 1) ** 2


def paste_scaled(frame, img, cx, cy, s):
    if s <= 0.02:
        return
    if abs(s - 1) > 0.01:
        img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def caption(frame, words, t, y):
    """Draw the current 2-3 word chunk; the word being spoken is yellow."""
    for ch in chunks(words):
        if ch[0][1] <= t < ch[-1][2] + 0.05:
            break
    else:
        return
    texts = [w[0].upper() for w in ch]
    size = 92
    while True:
        f = art.font(size)
        space = f.getlength(" ")
        total = sum(f.getlength(x) for x in texts) + space * (len(texts) - 1)
        if total <= W - 120 or size <= 50:
            break
        size -= 4
    d = ImageDraw.Draw(frame)
    x = W / 2 - total / 2
    for (w, t0, t1), txt in zip(ch, texts):
        col = (255, 214, 64) if t0 <= t < t1 + 0.05 else (255, 255, 255)
        d.text((x, y), txt, font=f, fill=col, anchor="lm", stroke_width=10, stroke_fill=(10, 10, 16))
        x += f.getlength(txt) + space


def draw_frame(shot: Shot, t: float, gt: float) -> Image.Image:
    sp = shot.spec
    prog = t / max(shot.dur, 0.01)
    bg = art.background(sp["scene"])
    z = 1.0 + 0.07 * prog + 0.07 * max(0.0, 1 - t / 0.18) ** 2  # quick punch-in on every cut
    ti = impact_time(shot)
    hit = ti is not None and t >= ti
    # the background is 15% oversized; crop toward the centre-bottom as we push in
    cw, chh = W * 1.15 / z, H * 1.15 / z
    x0 = (bg.width - cw) / 2
    y0 = (bg.height - chh) * 0.6
    frame = bg.crop((int(x0), int(y0), int(x0 + cw), int(y0 + chh))).resize((W, H), Image.BILINEAR).convert("RGBA")

    card_bottom = None
    if "card" in sp:
        c = sp["card"]
        rows = c["rows"]
        if c.get("alert"):
            shown = len(rows) + (1 if t > shot.dur * 0.3 else 0)
        else:
            shown = min(len(rows), int(t / (shot.dur / (len(rows) + 0.6))) + 1)
        img = art.card(c["title"], [tuple(r) for r in rows], shown, tuple(c["alert"]) if c.get("alert") else None)
        s = 0.92 + 0.08 * ease_pop(t / 0.25)
        cy = 260 + img.height / 2
        paste_scaled(frame, img, W / 2, cy, s)
        card_bottom = 260 + img.height

    if sp.get("orbit"):
        paste_scaled(frame, art.orbit(gt), W / 2, 1180, 1.0)

    if sp.get("lamps"):
        a, b = sp["lamps"]
        paste_scaled(frame, art.lamps(tuple(a), tuple(b), gt), W / 2, 610, 1.0)

    if sp.get("shrimp"):
        sx = sp["shrimp"].get("x", 0.5) if isinstance(sp["shrimp"], dict) else 0.5
        img = art.shrimp()
        bob = math.sin(gt * 2.5) * 12
        frame.alpha_composite(img, (int(W * sx - img.width / 2), int(1260 + bob)))

    if sp.get("speedlines"):
        frame.alpha_composite(art.speedlines(gt))

    ground_y = 1640
    if "prop" in sp:
        pr = sp["prop"]
        img = art.prop(pr["kind"], bool(pr.get("broken")) or hit)
        frame.alpha_composite(img, (int(W * pr.get("x", 0.72) - img.width / 2), int(ground_y - img.height)))

    if sp.get("punch") and sp.get("cast"):
        hero = sp["cast"][0]
        hx = W * hero["x"]
        tx = W * sp.get("prop", {}).get("x", 0.8) - 120
        reach = tx - hx - 60
        if ti is not None and ti - 0.05 <= t <= ti + 0.45:
            length = reach
        elif ti is not None and t < ti:
            length = 70  # cocked
        else:
            length = 120
        arm = art.club_arm(length)
        sp_arm = (int(hx + 30), int(1350 - arm.height / 2))
        sp["_arm"] = (arm, sp_arm)

    if sp.get("fire"):
        paste_scaled(frame, art.fire(gt), W / 2, 1460, 1.0)

    # characters, feet on a common ground line
    ground = 1640 if "card" not in sp else 1700
    for i, c in enumerate(sp.get("cast", [])):
        blink = (gt * 0.37 + i * 0.29) % 1.0 < 0.04
        scale = c.get("scale", 1.0) * (0.85 if "card" in sp else 1.0)
        img = art.character(c["who"], c.get("mood", "calm"), blink, scale)
        bob = math.sin(gt * 3.2 + i * 1.7) * 7
        squash = 1 + 0.06 * max(0, 1 - t / 0.2)  # tiny hop on shot start
        x = W * c["x"]
        frame.alpha_composite(img, (int(x - img.width / 2), int(ground - img.height + bob - (squash - 1) * 120)))

    if sp.get("_arm"):
        arm, pos = sp.pop("_arm")
        frame.alpha_composite(arm, pos)

    if ti is not None and ti <= t <= ti + 0.6:
        imp = sp["impact"]
        k = (t - ti) / 0.6
        bx = W * imp.get("x", sp.get("prop", {}).get("x", 0.6))
        paste_scaled(frame, art.burst(imp.get("text", "POW!")), bx, imp.get("y", 1200), ease_pop(k / 0.3) * (1 - 0.15 * k))

    # labels at the top
    if "kicker" in sp:
        paste_scaled(frame, art.pill(sp["kicker"], "kicker", 34), W / 2, 210, ease_pop((t - 0.0) / 0.2))
    if "label" in sp:
        lab = sp["label"]
        paste_scaled(frame, art.pill(lab["text"], lab.get("color", "dark"), 46), W / 2, 310, ease_pop((t - 0.08) / 0.22))

    cap_y = (card_bottom + 110) if card_bottom else 820
    caption(frame, shot.words, t, cap_y)
    out = frame.convert("RGB")
    if ti is not None and ti <= t <= ti + 0.35:  # screen shake + white flash
        k = 1 - (t - ti) / 0.35
        amp = 34 * k
        dx, dy = int(math.sin(t * 90) * amp), int(math.cos(t * 77) * amp)
        shaken = Image.new("RGB", (W, H), (255, 255, 255))
        shaken.paste(out, (dx, dy))
        out = Image.blend(shaken, Image.new("RGB", (W, H), (255, 255, 255)), max(0.0, 0.55 * (k - 0.6) / 0.4))
    return out


# ------------------------------------------------------------------ main

def render(story_path: str, out_path: str, preview: float | None = None):
    story = json.load(open(story_path, encoding="utf-8"))
    voice, speed = story.get("voice", "am_michael"), story.get("speed", 1.05)
    gap = story.get("gap", GAP)
    shots, voice_parts, t = [], [], 0.0
    for sp in story["shots"]:
        audio = speak(sp.get("say", sp["text"]), voice, speed)
        dur = len(audio) / SR
        sh = Shot(sp, start=t, dur=dur + gap)
        sh.words = word_times(sp["text"], dur)
        shots.append(sh)
        voice_parts.append(audio)
        voice_parts.append(np.zeros(int(gap * SR), dtype=np.float32))
        t += sh.dur
    total = t + 0.6
    if preview:
        total = min(total, preview)

    voice_track = np.concatenate(voice_parts)
    n = int(total * SR)
    mix = np.zeros(n, dtype=np.float32)
    mix[: min(n, len(voice_track))] += voice_track[:n] * 0.95
    mix += music_bed(total)[:n]
    for sh in shots:
        whoosh(sh.start - 0.06, mix)
        ti = impact_time(sh)
        if ti is not None:
            boom(sh.start + ti, mix)
        if "label" in sh.spec or "card" in sh.spec:
            pop(sh.start + 0.08, mix, 900)
        if "card" in sh.spec and not sh.spec["card"].get("alert"):
            rows = len(sh.spec["card"]["rows"])
            for k in range(1, rows):
                pop(sh.start + k * sh.dur / (rows + 0.6), mix, 1200)
        if sh.spec.get("card", {}).get("alert"):
            pop(sh.start + sh.dur * 0.3, mix, 300)
    mix = mix / max(1.0, np.abs(mix).max() / 0.95)

    with tempfile.TemporaryDirectory() as tmp:
        wav = f"{tmp}/mix.wav"
        write_wav(wav, mix)
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out_path],
            stdin=subprocess.PIPE,
        )
        frames = int(total * FPS)
        idx = 0
        for f in range(frames):
            gt = f / FPS
            while idx + 1 < len(shots) and gt >= shots[idx + 1].start:
                idx += 1
            sh = shots[idx]
            ff.stdin.write(draw_frame(sh, gt - sh.start, gt).tobytes())
        ff.stdin.close()
        ff.wait()
    return total
