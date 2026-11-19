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

from . import art, fx
from .art import H, W
from .tts import SR, speak

FPS = 30
GAP = 0.22  # seconds of air between shots


@dataclass
class Shot:
    spec: dict
    start: float = 0.0
    dur: float = 0.0
    countdown_at: float | None = None  # absolute time the on-screen countdown hits zero
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

def music_bed(seconds: float, mood: str = "light") -> np.ndarray:
    if mood == "tense":
        return tense_bed(seconds)
    return light_bed(seconds)


def tense_bed(seconds: float) -> np.ndarray:
    """Low drone + slow heartbeat pulse + a high shimmer. Original, generated."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    drone = 0.05 * np.sin(2 * np.pi * 55 * t) + 0.03 * np.sin(2 * np.pi * 82.4 * t) + 0.02 * np.sin(2 * np.pi * 110.6 * t)
    drone *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t)
    beat = np.zeros(n, dtype=np.float32)
    period = 0.95
    for k in range(int(seconds / period) + 1):
        for off, amp in ((0.0, 1.0), (0.22, 0.6)):
            i0 = int((k * period + off) * SR)
            m = int(0.18 * SR)
            if i0 + m >= n:
                continue
            pt = np.arange(m) / SR
            beat[i0:i0 + m] += np.sin(2 * np.pi * 50 * pt) * np.exp(-pt * 25) * 0.16 * amp
    shimmer = 0.008 * np.sin(2 * np.pi * 1318 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t))
    return (drone + beat + shimmer).astype(np.float32)


def light_bed(seconds: float) -> np.ndarray:
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


def word_time(shot, word: str, default: float | None = None) -> float | None:
    key = word.lower()
    for w, t0, t1 in shot.words:
        if re.sub(r"[^\w]", "", w.lower()) == key:
            return t0
    return default


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
    pop_k = ease_pop((t - ch[0][1] + 0.04) / 0.14)
    size = 92
    while True:
        f = art.font(size)
        space = f.getlength(" ")
        total = sum(f.getlength(x) for x in texts) + space * (len(texts) - 1)
        if total <= W - 120 or size <= 50:
            break
        size -= 4
    size = max(20, int(size * (0.82 + 0.18 * pop_k)))
    f = art.font(size)
    space = f.getlength(" ")
    total = sum(f.getlength(x) for x in texts) + space * (len(texts) - 1)
    sh_layer = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh_layer)
    sx = W / 2 - total / 2
    for txt in texts:  # soft drop shadow under the caption
        sd.text((sx + 6, 139), txt, font=f, fill=(0, 0, 0, 110), anchor="lm", stroke_width=12, stroke_fill=(0, 0, 0, 110))
        sx += f.getlength(txt) + space
    frame.alpha_composite(sh_layer, (0, int(y - 130)))
    d = ImageDraw.Draw(frame)
    x = W / 2 - total / 2
    for (w, t0, t1), txt in zip(ch, texts):
        col = (255, 214, 64) if t0 <= t < t1 + 0.05 else (255, 255, 255)
        d.text((x, y), txt, font=f, fill=col, anchor="lm", stroke_width=10, stroke_fill=(10, 10, 16))
        x += f.getlength(txt) + space


def draw_frame(shot: Shot, t: float, gt: float) -> Image.Image:
    sp = shot.spec
    prog = t / max(shot.dur, 0.01)
    scene = sp["scene"]
    if "switch" in sp:
        ts = word_time(shot, sp["switch"]["word"], shot.dur * 0.5)
        if t < ts:
            scene = sp["switch"]["from"]
    bg = art.background(scene)
    z = 1.0 + 0.07 * prog + 0.07 * max(0.0, 1 - t / 0.18) ** 2  # quick punch-in on every cut
    ti = impact_time(shot)
    hit = ti is not None and t >= ti
    # the background is 15% oversized; crop toward the centre-bottom as we push in
    cw, chh = W * 1.15 / z, H * 1.15 / z
    cam = (26 * math.sin(gt * 0.23), 14 * math.sin(gt * 0.31 + 1.0))
    x0 = (bg.width - cw) / 2 - cam[0] * 0.5
    y0 = (bg.height - chh) * 0.6 - cam[1] * 0.5
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

    if "sun" in sp:
        off = word_time(shot, sp["sun"].get("off_word", ""), None)
        if off is None or t < off:
            sx_, sy_ = W * sp["sun"].get("x", 0.72), sp["sun"].get("y", 420)
            fx.sun_rays(frame, sx_, sy_, gt, 0.9)
            paste_scaled(frame, art.sun_disc(1.0), sx_, sy_, 1.0 + 0.02 * math.sin(gt * 2))

    fx.particles(frame, scene, gt, cam)

    if "star" in sp:  # a planet still shining, then going out
        st = sp["star"]
        off = word_time(shot, st.get("off_word", ""), None)
        if off is None or t < off:
            pulse = 1 + 0.15 * math.sin(gt * 5)
            r = 22 * pulse
            x, y = W * st.get("x", 0.3), st.get("y", 480)
            glow = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse([100 - r * 3, 100 - r * 3, 100 + r * 3, 100 + r * 3], fill=(255, 230, 180, 70))
            ImageDraw.Draw(glow).ellipse([100 - r, 100 - r, 100 + r, 100 + r], fill=(255, 245, 220, 255))
            frame.alpha_composite(glow, (int(x - 100), int(y - 100)))
            if st.get("tag"):
                tag = art.pill(st["tag"], "kicker", 26)
                frame.alpha_composite(tag, (int(x - tag.width / 2), int(y + 40)))

    if "earth" in sp:
        e = art.earth(gt)
        drift = sp["earth"].get("drift", 0) * t
        ex, ey = W * sp["earth"].get("x", 0.35) + drift, sp["earth"].get("y", 1150)
        if sp["earth"].get("drift"):
            dd = ImageDraw.Draw(frame)
            for k in range(1, 6):
                dd.line([(ex - 200 - k * 60, ey - 60 + k * 24), (ex - 120 - k * 60, ey - 60 + k * 24)], fill=(160, 190, 255, 160), width=6)
        frame.alpha_composite(e, (int(ex - e.width / 2), int(ey - e.height / 2)))

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
        breath = 1 + 0.014 * math.sin(gt * 2.6 + i)
        img = img.resize((img.width, int(img.height * breath)), Image.BILINEAR)
        bob = math.sin(gt * 3.2 + i * 1.7) * 5
        hop = 0.0
        if t < 0.3:  # pop up on shot start
            hop = 70 * math.sin(math.pi * t / 0.3)
        if ti is not None and ti <= t <= ti + 0.4:  # jump on the impact word
            hop = 90 * math.sin(math.pi * (t - ti) / 0.4)
        x = W * c["x"] + cam[0]
        fx.ground_shadow(frame, x, ground - 4, img.width * 0.55 * (1 - hop / 400), scene != "park_day")
        frame.alpha_composite(img, (int(x - img.width / 2), int(ground - img.height + bob - hop)))

    if sp.get("_arm"):
        arm, pos = sp.pop("_arm")
        frame.alpha_composite(arm, pos)

    if ti is not None and ti <= t <= ti + 0.6 and sp["impact"].get("text"):
        imp = sp["impact"]
        k = (t - ti) / 0.6
        bx = W * imp.get("x", sp.get("prop", {}).get("x", 0.6))
        paste_scaled(frame, art.burst(imp.get("text", "POW!")), bx, imp.get("y", 1200), ease_pop(k / 0.3) * (1 - 0.15 * k))

    # labels at the top
    if "kicker" in sp:
        paste_scaled(frame, art.pill(sp["kicker"], "kicker", 34), W / 2, 210, ease_pop((t - 0.0) / 0.2))
    if "label" in sp:
        lab = sp["label"]
        paste_scaled(frame, art.pill(lab["text"], lab.get("color", "dark"), 46), W / 2, 310 - 50 * (1 - fx.ease_out((t - 0.08) / 0.25)), ease_pop((t - 0.08) / 0.22))
    if "counter" in sp:
        fx.counter(frame, sp["counter"], t, shot.dur, sp["counter"].get("y", 600))
    bars_bottom = None
    if "bars" in sp:
        by = sp["bars"].get("y", 470)
        fx.bars(frame, sp["bars"], t, by)
        bars_bottom = by + len(sp["bars"]["rows"]) * 162 + 70

    if sp.get("countdown") and shot.countdown_at is not None:
        left = max(0.0, shot.countdown_at - gt)
    if sp.get("countdown") and shot.countdown_at is not None and gt < shot.countdown_at + 0.5:
        txt = f"LIGHTS OUT IN 00:{left:04.1f}"
        img = art.pill(txt, "red" if left < 5 else "dark", 54)
        paste_scaled(frame, img, W / 2, 440, 1.0 + (0.06 * math.sin(gt * 12) if left < 5 else 0))

    cap_y = (card_bottom + 110) if card_bottom else (bars_bottom + 60 if bars_bottom else 820)
    frame.alpha_composite(fx.vignette(0.5))
    caption(frame, shot.words, t, cap_y)
    out = frame.convert("RGB")
    if ti is not None and ti <= t <= ti + 0.35:  # screen shake + white flash
        k = 1 - (t - ti) / 0.35
        amp = 34 * k * sp["impact"].get("shake", 1.0)
        dx, dy = int(math.sin(t * 90) * amp), int(math.cos(t * 77) * amp)
        shaken = Image.new("RGB", (W, H), (255, 255, 255))
        shaken.paste(out, (dx, dy))
        fc = (0, 0, 0) if sp["impact"].get("flash") == "black" else (255, 255, 255)
        out = Image.blend(shaken, Image.new("RGB", (W, H), fc), max(0.0, 0.55 * (k - 0.6) / 0.4))
    return out


# ------------------------------------------------------------------ main

WHIP = 0.24  # seconds for the slide between two different scenes


def start_scene(sh):
    return sh.spec.get("switch", {}).get("from", sh.spec["scene"])


def end_scene(sh):
    return sh.spec["scene"]


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
    for sh in shots:  # one countdown in the story, ending on the target shot's impact
        if sh.spec.get("countdown_target"):
            ti = impact_time(sh)
            target = sh.start + (ti if ti is not None else 0)
            for other in shots:
                other.countdown_at = target
    total = t + 0.6
    if preview:
        total = min(total, preview)

    voice_track = np.concatenate(voice_parts)
    n = int(total * SR)
    mix = np.zeros(n, dtype=np.float32)
    mix[: min(n, len(voice_track))] += voice_track[:n] * 0.95
    mix += music_bed(total, story.get("music", "light"))[:n]
    for sh in shots:
        whoosh(sh.start - 0.06, mix)
        if sh.spec.get("tick"):
            k = 0.0
            while k < sh.dur:
                pop(sh.start + k, mix, 2400)
                k += 0.5
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
        idx, last, prev_last = 0, None, None
        for f in range(frames):
            gt = f / FPS
            while idx + 1 < len(shots) and gt >= shots[idx + 1].start:
                idx += 1
                prev_last = last
            sh = shots[idx]
            t = gt - sh.start
            img = draw_frame(sh, t, gt)
            last = img
            if idx > 0 and prev_last is not None and t < WHIP and start_scene(sh) != end_scene(shots[idx - 1]):
                img = fx.whip(prev_last, img, t / WHIP)
            ff.stdin.write(img.tobytes())
        ff.stdin.close()
        ff.wait()
    return total
