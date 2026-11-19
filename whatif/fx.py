"""Per-frame polish: light, particles, vignette, transitions, counters and comparison bars.

Everything here is drawn in code. Positions come from fixed random seeds so a
particle keeps its path from frame to frame.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import art

W, H = art.W, art.H


def ease_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def ease_in_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- light

@lru_cache(maxsize=4)
def vignette(strength: float = 0.55) -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.62)) ** 2)
    a = np.clip((d - 0.55) / 0.6, 0, 1) ** 1.6 * 255 * strength
    img = Image.new("RGBA", (W, H), (6, 4, 18, 0))
    img.putalpha(Image.fromarray(a.astype(np.uint8)))
    return img


@lru_cache(maxsize=2)
def _rays() -> Image.Image:
    s = 1400
    m = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(m)
    c = s / 2
    for k in range(14):
        a = k / 14 * math.tau
        w = 0.07 if k % 2 else 0.04
        d.polygon([(c, c), (c + math.cos(a - w) * c, c + math.sin(a - w) * c), (c + math.cos(a + w) * c, c + math.sin(a + w) * c)], fill=60)
    m = m.filter(ImageFilter.GaussianBlur(18))
    fade = Image.new("L", (s, s), 0)
    ImageDraw.Draw(fade).ellipse([0, 0, s, s], fill=255)
    fade = fade.filter(ImageFilter.GaussianBlur(200))
    from PIL import ImageChops
    m = ImageChops.multiply(m, fade)
    img = Image.new("RGBA", (s, s), (255, 236, 170, 0))
    img.putalpha(m)
    return img


def sun_rays(frame: Image.Image, x: float, y: float, gt: float, alpha: float = 1.0):
    if alpha <= 0:
        return
    r = _rays().rotate(gt * 7 % 360, resample=Image.BILINEAR)
    if alpha < 1:
        r.putalpha(r.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(r, (int(x - r.width / 2), int(y - r.height / 2)))


def grade(frame: Image.Image, color, amount: float):
    """Wash the whole frame toward a colour (cold blue after the blackout, etc)."""
    if amount <= 0:
        return
    frame.alpha_composite(Image.new("RGBA", (W, H), (*color, int(255 * amount))))


# ---------------------------------------------------------------- particles

@lru_cache(maxsize=4)
def _cloud(seed: int) -> Image.Image:
    rnd = random.Random(seed)
    img = Image.new("RGBA", (520, 220), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _ in range(7):
        x, y, r = rnd.uniform(110, 410), rnd.uniform(100, 140), rnd.uniform(50, 90)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 235))
    d.rectangle([90, 140, 430, 190], fill=(0, 0, 0, 0))
    d.rounded_rectangle([80, 120, 440, 180], radius=30, fill=(255, 255, 255, 235))
    return img.filter(ImageFilter.GaussianBlur(1.5))


def _rnd_points(seed: int, n: int):
    rnd = random.Random(seed)
    return [(rnd.random(), rnd.random(), rnd.random(), rnd.random()) for _ in range(n)]


def particles(frame: Image.Image, scene: str, gt: float, cam=(0.0, 0.0)):
    """Ambient life for each scene. cam shifts the layer for a touch of parallax."""
    ox, oy = cam
    if scene == "park_day":
        for i, (x0, y0, sp, _) in enumerate(_rnd_points(7, 3)):
            c = _cloud(i)
            x = (x0 * (W + 600) + gt * (14 + sp * 10)) % (W + 600) - 560 + ox * 0.5
            frame.alpha_composite(c, (int(x), int(120 + y0 * 330 + oy * 0.5)))
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if scene in ("park_dark", "park_frozen", "space", "mind"):
        top = H * (0.55 if scene.startswith("park") else 1.0)
        for x0, y0, sp, ph in _rnd_points(11, 70):  # twinkling stars
            a = 0.5 + 0.5 * math.sin(gt * (1.5 + sp * 3) + ph * 6.28)
            x, y = x0 * W + ox * 0.3, y0 * top + oy * 0.3
            r = 2 + sp * 3
            col = (255, 255, 255, int(220 * a))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)
            if sp > 0.7:
                d.line([(x - r * 4, y), (x + r * 4, y)], fill=(255, 255, 255, int(120 * a)), width=2)
                d.line([(x, y - r * 4), (x, y + r * 4)], fill=(255, 255, 255, int(120 * a)), width=2)
    if scene in ("park_frozen",):
        for x0, y0, sp, ph in _rnd_points(5, 160):  # snow
            y = (y0 * H + gt * (90 + sp * 160)) % H
            x = (x0 * W + math.sin(gt * (0.8 + sp) + ph * 6.28) * 40 + ox) % W
            r = 3 + sp * 6
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(150 + 90 * sp)))
    if scene == "ocean_cut":
        for x0, y0, sp, ph in _rnd_points(9, 90):  # marine snow drifting down
            y = H * 0.3 + (y0 * H * 0.6 + gt * (20 + sp * 25)) % (H * 0.56)
            x = x0 * W + math.sin(gt * 0.6 + ph * 6.28) * 18
            r = 1.5 + sp * 2.5
            d.ellipse([x - r, y - r, x + r, y + r], fill=(190, 220, 255, 110))
        for vx in (0.3, 0.62, 0.85):  # bubbles rising from the vents
            for k, (x0, y0, sp, ph) in enumerate(_rnd_points(int(vx * 100), 7)):
                life = (gt * (0.35 + sp * 0.3) + ph) % 1.0
                y = H * 0.74 - life * H * 0.42
                x = W * vx + (x0 - 0.5) * 60 + math.sin(gt * 3 + k) * 10
                r = 5 + sp * 8
                d.ellipse([x - r, y - r, x + r, y + r], outline=(210, 235, 255, int(200 * (1 - life))), width=3)
    if scene == "cave":
        for x0, y0, sp, ph in _rnd_points(13, 50):  # warm dust in the lamp light
            y = (y0 * H * 0.6 + H * 0.15 - gt * (8 + sp * 14)) % (H * 0.6) + H * 0.1
            x = x0 * W + math.sin(gt * 0.7 + ph * 6.28) * 30
            r = 2 + sp * 3
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 220, 150, int(90 + 100 * sp)))
    frame.alpha_composite(layer)


def ground_shadow(frame: Image.Image, x: float, y: float, w: float, dark: bool):
    s = Image.new("RGBA", (int(w * 1.6), 90), (0, 0, 0, 0))
    ImageDraw.Draw(s).ellipse([w * 0.3, 25, w * 1.3, 65], fill=(0, 0, 0, 70 if dark else 55))
    s = s.filter(ImageFilter.GaussianBlur(8))
    frame.alpha_composite(s, (int(x - s.width / 2), int(y - 45)))


# ---------------------------------------------------------------- data graphics

def counter(frame: Image.Image, spec: dict, t: float, dur: float, y: float = 600):
    """A big number that rolls from `from` to `to`, e.g. a temperature falling."""
    a, b = spec["from"], spec["to"]
    k = ease_in_out((t - 0.25) / max(0.4, dur * spec.get("speed", 0.65)))
    v = a + (b - a) * k
    dec = spec.get("decimals", 0)
    num = f"{v:,.{dec}f}".replace("-", "−")
    txt = f"{num}{spec.get('unit', '')}"
    hot, cold = (255, 214, 64), (130, 200, 255)
    col = art._lerp(spec.get("color_from", hot), spec.get("color_to", cold), k) if spec.get("shift", True) else hot
    f = art.font(190)
    lab = art.font(40)
    d = ImageDraw.Draw(frame)
    if spec.get("label"):
        d.text((W / 2, y - 120), spec["label"], font=lab, fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(10, 10, 16))
    bump = 1 + 0.04 * math.sin(t * 40) * (1 - k) * (k > 0)
    fs = art.font(int(190 * bump))
    d.text((W / 2, y), txt, font=fs, fill=col, anchor="mm", stroke_width=14, stroke_fill=(10, 10, 16))


def bars(frame: Image.Image, spec: dict, t: float, y: float = 520):
    """Horizontal comparison bars that grow one after another."""
    rows = spec["rows"]
    vmax = max(r["value"] for r in rows)
    x0, x1 = (90, W - 90) if W < H else (int(W * 0.3), W - 120)
    rh, gap = 74, 44
    title = spec.get("title")
    d = ImageDraw.Draw(frame)
    panel_h = len(rows) * (rh + gap + 44) + (70 if title else 0) + 30
    p = Image.new("RGBA", (x1 - x0 + 60, panel_h), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius=28, fill=(10, 12, 24, 170))
    frame.alpha_composite(p, (x0 - 30, int(y - 30)))
    yy = y
    if title:
        d.text(((x0 + x1) / 2, yy + 14), title, font=art.font(38), fill=(255, 214, 64), anchor="mm")
        yy += 70
    for i, r in enumerate(rows):
        start = 0.2 + i * 0.7
        k = ease_out((t - start) / 0.9)
        d.text((x0, yy), r["name"], font=art.font(36), fill=(235, 238, 250), anchor="lm")
        yy += 44
        full = (x1 - x0) * r["value"] / vmax
        w = max(18, full * k)
        col = (232, 70, 60) if r.get("hl") else (120, 132, 160)
        d.rounded_rectangle([x0, yy, x0 + w, yy + rh], radius=rh // 2, fill=col)
        if k > 0.05:
            val = f"{r['value'] * k:,.{r.get('decimals', 0)}f} {r.get('unit', '')}".strip()
            inside = w > 300
            d.text((x0 + w - 24 if inside else x0 + w + 20, yy + rh / 2), val, font=art.font(40),
                   fill=(255, 255, 255), anchor="rm" if inside else "lm", stroke_width=0 if inside else 5, stroke_fill=(10, 10, 16))
        yy += rh + gap


# ---------------------------------------------------------------- transitions

def whip(prev: Image.Image, cur: Image.Image, k: float) -> Image.Image:
    """Slide the new shot in from the right with a horizontal motion blur."""
    e = ease_in_out(k)
    off = int(W * (1 - e))
    out = Image.new("RGB", (W, H))
    out.paste(prev, (off - W, 0))
    out.paste(cur, (off, 0))
    blur = int(70 * math.sin(math.pi * e))
    if blur < 4:
        return out
    a = np.asarray(out).astype(np.float32)
    acc = np.zeros_like(a)
    n = 6
    for j in range(n):
        acc += np.roll(a, int(blur * (j / (n - 1) - 0.5)), axis=1)
    return Image.fromarray((acc / n).astype(np.uint8))


def chapter(frame: Image.Image, spec: dict, t: float, y: float):
    """Chapter title band that slides in: small 'CHAPTER 2' over a big title."""
    k = ease_out(t / 0.35)
    band_h = 300
    band = Image.new("RGBA", (W, band_h), (12, 10, 24, int(215 * k)))
    frame.alpha_composite(band, (0, int(y - band_h / 2)))
    d = ImageDraw.Draw(frame)
    x = W / 2 + (1 - k) * -200
    d.text((x, y - 70), spec.get("kicker", f"CHAPTER {spec.get('num', '')}").strip(), font=art.font(44),
           fill=(255, 196, 54), anchor="mm")
    title = spec["title"]
    size = 110
    while art.font(size).getlength(title) > W - 120 and size > 50:
        size -= 6
    d.text((W / 2 + (1 - k) * 200, y + 30), title, font=art.font(size), fill=(255, 255, 255), anchor="mm",
           stroke_width=8, stroke_fill=(10, 10, 16))
