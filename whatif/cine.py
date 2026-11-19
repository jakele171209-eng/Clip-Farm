"""Cinematic style tests: the same 10-second story beat in two looks.

  noir  - realistic silhouettes, volumetric light, fog, rain, film grain, serif subtitles
  comic - graphic-novel panels: ink outlines, halftone shading, caption boxes

python -m whatif.cine noir out/style-noir.mp4
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
import tempfile
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from .render import FPS, boom, hit, tense_bed, write_wav
from .tts import SR, speak

W, H = 1080, 1920
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
COMIC = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"


def font(path, size):
    return ImageFont.truetype(path, size)


def glow(img, x, y, r, col, a=150, blur=None):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).ellipse([x - r, y - r, x + r, y + r], fill=a)
    m = m.filter(ImageFilter.GaussianBlur(blur or r / 2.5))
    img.paste(col, (0, 0), m)


def cone(img, apex, left, right, col, a=90, blur=40):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).polygon([apex, left, right], fill=a)
    m = m.filter(ImageFilter.GaussianBlur(blur))
    img.paste(col, (0, 0), m)


def person(d, x, base, h, col, pose="stand", facing=1):
    """A realistic-proportion human silhouette, ~7.5 heads tall. base = feet y."""
    u = h / 7.5
    top = base - h
    hx, hy = x, top + 0.55 * u
    d.ellipse([hx - 0.42 * u, hy - 0.55 * u, hx + 0.42 * u, hy + 0.55 * u], fill=col)  # head
    d.polygon([(x - 0.2 * u, hy + 0.3 * u), (x + 0.2 * u, hy + 0.3 * u), (x + 0.32 * u, hy + 1.05 * u), (x - 0.32 * u, hy + 1.05 * u)], fill=col)
    sh = hy + 1.1 * u  # shoulder line
    d.chord([x - 1.0 * u, sh - 0.35 * u, x + 1.0 * u, sh + 0.9 * u], 180, 360, fill=col)
    d.polygon([(x - 1.0 * u, sh + 0.25 * u), (x + 1.0 * u, sh + 0.25 * u), (x + 0.72 * u, base - 3.4 * u), (x - 0.72 * u, base - 3.4 * u)], fill=col)
    d.polygon([(x - 0.75 * u, base - 3.5 * u), (x + 0.75 * u, base - 3.5 * u), (x + 0.7 * u, base - 2.9 * u), (x - 0.7 * u, base - 2.9 * u)], fill=col)
    for sgn in (-1, 1):  # legs, slightly apart
        d.polygon([(x + sgn * 0.04 * u, base - 3.0 * u), (x + sgn * 0.7 * u, base - 3.0 * u), (x + sgn * 0.58 * u, base - 0.1 * u),
                   (x + sgn * 0.2 * u, base - 0.1 * u)], fill=col)
        fx0, fx1 = sorted((x + sgn * 0.15 * u, x + sgn * 0.8 * u))
        d.ellipse([fx0, base - 0.25 * u, fx1, base + 0.05 * u], fill=col)
    hands = {"stand": ((-1.2, 3.3), (1.2, 3.3)), "slump": ((-1.05, 3.1), (1.05, 3.1)), "phone": ((-1.2, 3.3), (0.3, 5.8))}[pose]
    for sgn, (ax, ay) in zip((-1, 1), hands):  # tapered arms hanging a little away from the body
        sx_, sy_ = x + sgn * 0.88 * u, sh + 0.2 * u
        ex, ey = x + ax * u, base - ay * u
        nx, ny = (ey - sy_), -(ex - sx_)
        ln = math.hypot(nx, ny) or 1
        nx, ny = nx / ln, ny / ln
        d.polygon([(sx_ + nx * 0.26 * u, sy_ + ny * 0.26 * u), (sx_ - nx * 0.26 * u, sy_ - ny * 0.26 * u),
                   (ex - nx * 0.15 * u, ey - ny * 0.15 * u), (ex + nx * 0.15 * u, ey + ny * 0.15 * u)], fill=col)
        d.ellipse([ex - 0.2 * u, ey - 0.25 * u, ex + 0.2 * u, ey + 0.25 * u], fill=col)


def rimmed(img, draw_fn, col, light, dx, dy, width=6):
    """Draw a silhouette with a thin rim of light on the side facing the light source."""
    m = Image.new("L", img.size, 0)
    draw_fn(ImageDraw.Draw(m), 255)
    sh = Image.new("L", img.size, 0)
    sh.paste(m, (dx * width, dy * width))
    rim = ImageChops.subtract(m, sh).filter(ImageFilter.GaussianBlur(width / 2))
    img.paste(col, (0, 0), m)
    img.paste(light, (0, 0), rim)


def profile(d, x, y, s, col):
    """Head-and-shoulders in profile facing right: brow, nose, lips, chin."""
    pts = [(-0.9, -1.6), (-0.2, -1.95), (0.35, -1.8), (0.62, -1.3), (0.66, -0.95), (0.6, -0.85), (0.9, -0.5),
           (0.62, -0.38), (0.66, -0.25), (0.6, -0.15), (0.64, -0.05), (0.58, 0.08), (0.55, 0.25), (0.35, 0.45),
           (0.05, 0.5), (0.0, 0.9), (0.9, 1.5), (1.4, 2.6), (-1.8, 2.6), (-1.3, 1.4), (-0.95, 0.6), (-1.1, -0.6)]
    d.polygon([(x + px * s, y + py * s) for px, py in pts], fill=col)


# ---------------------------------------------------------------- plates (drawn once at 2x, cached)

S2 = 2


@lru_cache(maxsize=8)
def plate(name: str) -> Image.Image:
    bw, bh = int(W * 1.12) * S2, int(H * 1.12) * S2
    rnd = random.Random(name)
    if name == "city":
        img = Image.new("RGB", (bw, bh))
        g = np.linspace(0, 1, bh)[:, None]
        top, bot = np.array([6, 10, 22]), np.array([26, 40, 58])
        arr = (top + (bot - top) * g).astype(np.uint8)[:, :, None].repeat(1, 2)
        img = Image.fromarray(np.broadcast_to(arr.reshape(bh, 1, 3), (bh, bw, 3)).copy())
        glow(img, bw * 0.45, bh * 0.5, 230 * S2, (225, 232, 255), 255, 4 * S2)  # huge low moon behind you
        glow(img, bw * 0.45, bh * 0.5, 700 * S2, (110, 140, 200), 120)
        d = ImageDraw.Draw(img)
        for layer, (col, base, hmin, hmax) in enumerate((((22, 30, 44), 0.66, 120, 260), ((12, 16, 24), 0.74, 140, 330))):
            x = 0
            while x < bw:
                w = rnd.uniform(90, 240) * S2
                h = rnd.uniform(hmin, hmax) * S2
                d.rectangle([x, bh * base - h, x + w, bh], fill=col)
                if layer == 1 and rnd.random() < 0.25:  # one window still lit, far apart
                    wx, wy = x + rnd.uniform(20, w / S2 - 40) * S2, bh * base - h + rnd.uniform(40, h / S2 - 80) * S2
                    d.rectangle([wx, wy, wx + 22 * S2, wy + 30 * S2], fill=(255, 196, 120))
                x += w + rnd.uniform(4, 20) * S2
        d.rectangle([0, bh * 0.8, bw, bh], fill=(4, 5, 8))  # rooftop
        d.rectangle([0, bh * 0.795, bw, bh * 0.8], fill=(40, 50, 70))
        rimmed(img, lambda dd, c: person(dd, bw * 0.42, bh * 0.8, 560 * S2, c, "slump"), (2, 2, 4), (190, 210, 255), 1, 1, 5 * S2)
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        rim = Image.new("RGB", (bw, bh), (0, 0, 0))
        return img.resize((bw // S2, bh // S2), Image.LANCZOS)
    if name == "kitchen":
        img = Image.new("RGB", (bw, bh), (8, 6, 6))
        d = ImageDraw.Draw(img)
        d.rectangle([bw * 0.18, bh * 0.18, bw * 0.82, bh * 0.92], fill=(14, 10, 9))  # doorway
        glow(img, bw * 0.62, bh * 0.66, 520 * S2, (255, 120, 40), 170)  # stove light
        cone(img, (bw * 0.62, bh * 0.62), (bw * 0.05, bh * 1.1), (bw * 1.1, bh * 0.9), (255, 140, 60), 70, 60 * S2)
        d = ImageDraw.Draw(img)
        d.rectangle([bw * 0.45, bh * 0.66, bw * 0.95, bh * 0.92], fill=(6, 4, 4))  # counter
        d.rectangle([0, bh * 0.92, bw, bh], fill=(4, 3, 3))
        rimmed(img, lambda dd, c: person(dd, bw * 0.48, bh * 0.92, 950 * S2, c, "slump"), (3, 2, 2), (255, 150, 70), -1, 0, 7 * S2)
        d.rectangle([0, 0, bw * 0.18, bh], fill=(2, 2, 2))  # door frame
        d.rectangle([bw * 0.82, 0, bw, bh], fill=(2, 2, 2))
        return img.resize((bw // S2, bh // S2), Image.LANCZOS)
    if name == "face":
        img = Image.new("RGB", (bw, bh), (2, 3, 6))
        glow(img, bw * 0.72, bh * 0.56, 600 * S2, (60, 120, 255), 140)
        d = ImageDraw.Draw(img)
        rimmed(img, lambda dd, c: profile(dd, bw * 0.4, bh * 0.45, 330 * S2, c), (1, 1, 2), (90, 150, 255), -1, 0, 6 * S2)
        d = ImageDraw.Draw(img)
        # phone in hand, screen facing the face
        d.rounded_rectangle([bw * 0.66, bh * 0.5, bw * 0.78, bh * 0.66], radius=30 * S2, fill=(170, 210, 255))
        d.text((bw * 0.72, bh * 0.555), "47", font=font(SERIF_B, 90 * S2), fill=(200, 30, 30), anchor="mm")
        d.text((bw * 0.72, bh * 0.6), "missed", font=font(SERIF, 34 * S2), fill=(30, 40, 60), anchor="mm")
        img = img.filter(ImageFilter.GaussianBlur(0.8))
        return img.resize((bw // S2, bh // S2), Image.LANCZOS)
    raise KeyError(name)


# ---------------------------------------------------------------- per-frame finishing

RNG = np.random.default_rng(7)
GRAIN = [RNG.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]


@lru_cache(maxsize=2)
def vign():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.55)) ** 2)
    return np.clip(1.15 - dd ** 2 * 0.75, 0.15, 1.0)[:, :, None]


def finish(img: Image.Image, f: int, grade=(1.0, 1.0, 1.0), grain=10.0) -> Image.Image:
    a = np.asarray(img).astype(np.float32)
    a *= vign()
    a *= np.array(grade, dtype=np.float32)
    g = GRAIN[f % len(GRAIN)]
    g = np.kron(g, np.ones((2, 2), dtype=np.float32))[:H, :W, None]
    a += g * grain
    a[:150] = 0  # letterbox
    a[-150:] = 0
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def camera(plate_img, k, zoom=(1.0, 1.08), pan=(0, 0)):
    z = zoom[0] + (zoom[1] - zoom[0]) * k
    cw, ch = plate_img.width / z, plate_img.height / z
    x0 = (plate_img.width - cw) / 2 + pan[0] * k
    y0 = (plate_img.height - ch) / 2 + pan[1] * k
    return plate_img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)


def rain(img, t):
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(3)
    for _ in range(220):
        x0, y0, sp = rnd.uniform(0, W + 300), rnd.uniform(0, H), rnd.uniform(1800, 2600)
        y = (y0 + t * sp) % (H + 200) - 100
        x = x0 - (y / H) * 300
        d.line([(x, y), (x - 10, y + 42)], fill=(180, 200, 230, 70), width=2)


def fog(img, t, col=(140, 160, 190), a=60):
    m = Image.new("L", (W // 4, H // 4), 0)
    d = ImageDraw.Draw(m)
    rnd = random.Random(9)
    for _ in range(14):
        x = (rnd.uniform(0, W // 4) + t * rnd.uniform(4, 10)) % (W // 4 + 200) - 100
        y = rnd.uniform(H * 0.45 / 4, H * 0.8 / 4)
        r = rnd.uniform(60, 120)
        d.ellipse([x - r, y - r * 0.35, x + r, y + r * 0.35], fill=a)
    m = m.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR)
    img.paste(col, (0, 0), m)


def subtitle(img, text, k, y=1500, style="noir"):
    text = text.replace(" Except you.", "")
    if not text or k <= 0:
        return
    d = ImageDraw.Draw(img, "RGBA")
    a = int(255 * min(1, k * 3))
    if style == "noir":
        f = font(SERIF, 58)
        lines = wrap(text, f, W - 200)
        for i, ln in enumerate(lines):
            d.text((W / 2, y + i * 78), ln, font=f, fill=(240, 236, 228, a), anchor="mm")
    else:
        f = font(COMIC, 50)
        lines = wrap(text.upper(), f, W - 260)
        bh = len(lines) * 66 + 40
        d.rectangle([90, 190, W - 90, 190 + bh], fill=(255, 226, 90, a), outline=(10, 10, 10, a), width=7)
        for i, ln in enumerate(lines):
            d.text((W / 2, 190 + 52 + i * 66), ln, font=f, fill=(10, 10, 10, a), anchor="mm")


def wrap(text, f, width):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if f.getlength(t) > width and cur:
            out.append(cur)
            cur = w
        else:
            cur = t
    return out + [cur]


# ---------------------------------------------------------------- comic treatment

@lru_cache(maxsize=1)
def dots():
    yy, xx = np.mgrid[0:H, 0:W]
    return ((np.sin(xx * 0.45) * np.sin(yy * 0.45)) * 0.5 + 0.5).astype(np.float32)


def comicify(img: Image.Image, palette) -> Image.Image:
    """Posterize to a few inks, halftone the shadows, ink the edges."""
    g = np.asarray(ImageOps.grayscale(img)).astype(np.float32) / 255
    g = np.clip(g * 2.2, 0, 1)
    levels = np.array([0.0, 0.25, 0.55, 1.0])
    idx = np.digitize(g, [0.12, 0.38, 0.7])
    out = np.zeros((H, W, 3), np.float32)
    for i, col in enumerate(palette):
        out[idx == i] = col
    shade = (g < 0.38) & (dots() > g * 2.4)
    out[shade] *= 0.55
    edges = np.asarray(img.convert("L").filter(ImageFilter.FIND_EDGES)).astype(np.float32)
    out[edges > 18] = (12, 10, 14)
    return Image.fromarray(out.astype(np.uint8))


# ---------------------------------------------------------------- the beat

SHOTS = [  # plate, seconds, line, camera zoom, pan
    ("city", 3.6, "At 3:12 in the morning, the whole city went quiet.", (1.0, 1.1), (0, -40)),
    ("kitchen", 3.4, "By breakfast, your mother was asleep. Standing up.", (1.06, 1.0), (30, 0)),
    ("face", 3.4, "Forty-seven missed calls. Nobody is awake. Except you.", (1.0, 1.12), (40, 10)),
]


def render_sample(style: str, out_path: str):
    lines = [s[2] for s in SHOTS]
    voice = "bm_george" if style == "noir" else "am_michael"
    parts = [speak(t, voice, 0.92 if style == "noir" else 1.1) for t in lines]
    durs = [max(s[1], len(p) / SR + 0.5) for s, p in zip(SHOTS, parts)]
    total = sum(durs) + 0.8
    n = int(total * SR)
    mix = tense_bed(total)[:n] * 1.2
    t = 0.3
    starts = []
    for p, dur in zip(parts, durs):
        starts.append(t)
        mix[int(t * SR): int(t * SR) + len(p)] += p
        t += dur
    boom(starts[-1] + durs[-1] - 1.2, mix)
    hit(starts[-1] + durs[-1] - 1.2, mix)
    mix = mix / max(1.0, np.abs(mix).max() / 0.95)
    pal_list = [((14, 12, 30), (60, 70, 140), (210, 120, 70), (255, 236, 200)),
                ((20, 10, 8), (120, 50, 30), (240, 140, 60), (255, 230, 170)),
                ((8, 10, 30), (40, 80, 170), (120, 180, 255), (235, 245, 255))]
    with tempfile.TemporaryDirectory() as tmp:
        write_wav(f"{tmp}/a.wav", mix)
        ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-i", f"{tmp}/a.wav", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                               "-af", "loudnorm=I=-14:TP=-1.5", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path],
                              stdin=subprocess.PIPE)
        for fi in range(int(total * FPS)):
            gt = fi / FPS
            i = max(0, sum(1 for s in starts if gt >= s) - 1)
            name, _, line, zoom, pan = SHOTS[i]
            lt = gt - starts[i]
            k = min(1.0, max(0.0, lt / durs[i]))
            img = camera(plate(name), k, zoom, pan)
            if name == "city":
                fog(img, gt)
                rain(img, gt)
            if name == "kitchen":
                fog(img, gt, (255, 150, 90), 40)
                flick = 0.9 + 0.1 * math.sin(gt * 23) * math.sin(gt * 7)
                img = Image.fromarray(np.clip(np.asarray(img) * flick, 0, 255).astype(np.uint8))
            if style == "comic":
                img = comicify(img, pal_list[i])
                d = ImageDraw.Draw(img)
                d.rectangle([24, 24, W - 24, H - 24], outline=(10, 10, 10), width=16)
                subtitle(img, line, lt / 0.4, style="comic")
                if name == "face" and lt > durs[i] - 1.3:
                    bf = font(COMIC, 150)
                    d.text((W / 2, 1450), "EXCEPT YOU.", font=bf, fill=(230, 40, 40), anchor="mm", stroke_width=12, stroke_fill=(10, 10, 10))
                frame = img
            else:
                if name == "face" and lt > durs[i] - 1.3:  # hard cut to black on the last words
                    img = Image.new("RGB", (W, H), (0, 0, 0))
                    ImageDraw.Draw(img).text((W / 2, H / 2), "Except you.", font=font(SERIF, 96), fill=(235, 230, 220), anchor="mm")
                    frame = finish(img, fi, grain=8)
                else:
                    subtitle(img, line, lt / 0.6)
                    grade = {"city": (0.85, 1.0, 1.15), "kitchen": (1.15, 0.98, 0.85), "face": (0.85, 0.95, 1.2)}[name]
                    fade = min(1.0, lt / 0.35, (durs[i] - lt) / 0.25 + 0.2)
                    frame = finish(img, fi, grade)
                    if fade < 1:
                        frame = Image.fromarray((np.asarray(frame) * max(0.0, fade)).astype(np.uint8))
            ff.stdin.write(frame.tobytes())
        ff.stdin.close()
        ff.wait()
    return total


if __name__ == "__main__":
    print(render_sample(sys.argv[1], sys.argv[2]))
