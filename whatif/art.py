"""Flat 2D art drawn in code: backgrounds, characters, labels and cards.

Everything is drawn at 2x and scaled down, which gives smooth edges without
an anti-aliasing library. All art here is original to this project.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920


def set_size(w: int, h: int):
    """Change the frame size (vertical Shorts or 16:9 long-form)."""
    global W, H
    if (w, h) != (W, H):
        W, H = w, h
        background.cache_clear()
SS = 2  # supersampling factor

FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


@lru_cache(maxsize=64)
def font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if weight == "bold" else FONT_SEMI
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def _gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGB", (w, h), top)
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=_lerp(top, bottom, y / max(1, h - 1)))
    return img


def _down(img: Image.Image, size=None) -> Image.Image:
    size = size or (img.width // SS, img.height // SS)
    return img.resize(size, Image.LANCZOS)


# ---------------------------------------------------------------- backgrounds

PALETTES = {
    "ship_day": dict(sky=((150, 196, 230), (226, 238, 246)), hill=(206, 222, 234), hill2=(186, 206, 222),
                     ice=(222, 236, 244), ground=(240, 246, 250), hull=(112, 74, 52), dark=False),
    "ship_night": dict(sky=((14, 22, 48), (44, 58, 96)), hill=(46, 60, 92), hill2=(36, 48, 78),
                       ice=(70, 90, 128), ground=(86, 104, 140), hull=(58, 40, 32), dark=True),
    "spring": dict(sky=((250, 196, 140), (255, 236, 200)), hill=(132, 170, 112), hill2=(110, 150, 96),
                   ice=(96, 150, 196), ground=(150, 186, 120), hull=(112, 74, 52), dark=False),
    "village": dict(sky=((168, 200, 226), (232, 240, 246)), hill=(198, 216, 228), hill2=(178, 200, 214),
                    ice=(222, 236, 244), ground=(238, 244, 248), hull=(112, 74, 52), dark=False),
}


def _ship(d, cx, base, s, hull, sails_up, dark):
    """A 16th-century three-masted ship, side view."""
    hw = 230 * s
    d.polygon([(cx - hw, base - 70 * s), (cx + hw, base - 90 * s), (cx + hw * 0.8, base), (cx - hw * 0.85, base)], fill=hull)
    d.rectangle([cx + hw * 0.45, base - 150 * s, cx + hw, base - 85 * s], fill=hull)
    d.rectangle([cx - hw, base - 120 * s, cx - hw * 0.6, base - 68 * s], fill=hull)
    stripe = _lerp(hull, (255, 220, 160), 0.35)
    d.line([(cx - hw * 0.9, base - 40 * s), (cx + hw * 0.85, base - 48 * s)], fill=stripe, width=int(8 * s))
    mast = _lerp(hull, (0, 0, 0), 0.25)
    sail = (238, 230, 214) if not dark else (150, 150, 160)
    for mx, mh in ((-0.45, 330), (0.05, 420), (0.55, 300)):
        x = cx + hw * mx
        d.rectangle([x - 6 * s, base - (mh + 70) * s, x + 6 * s, base - 70 * s], fill=mast)
        if sails_up:
            d.polygon([(x - 90 * s, base - (mh + 30) * s), (x + 90 * s, base - (mh + 30) * s),
                       (x + 80 * s, base - (mh * 0.45 + 70) * s), (x - 80 * s, base - (mh * 0.45 + 70) * s)], fill=sail)
        else:  # furled sails = thin rolls on the yards
            d.rounded_rectangle([x - 80 * s, base - (mh + 30) * s, x + 80 * s, base - (mh + 12) * s], radius=8 * s, fill=sail)
    if dark:  # lantern
        lx, ly = cx + hw * 0.7, base - 170 * s
        d.ellipse([lx - 14 * s, ly - 14 * s, lx + 14 * s, ly + 14 * s], fill=(255, 210, 120))


def _longhouse(d, x, base, w, h, fill):
    d.rounded_rectangle([x, base - h, x + w, base], radius=h * 0.9, fill=fill)
    d.rectangle([x, base - h * 0.5, x + w, base], fill=fill)
    line = _lerp(fill, (0, 0, 0), 0.2)
    for i in range(1, 6):
        lx = x + w * i / 6
        d.line([(lx, base - h * 0.95), (lx, base)], fill=line, width=4)
    d.rectangle([x + w * 0.45, base - h * 0.45, x + w * 0.55, base], fill=_lerp(fill, (0, 0, 0), 0.5))


def _pine(d, x, base, h, col):
    for i in range(3):
        y0 = base - h + i * h * 0.25
        w = h * (0.22 + i * 0.1)
        d.polygon([(x, y0), (x + w, y0 + h * 0.42), (x - w, y0 + h * 0.42)], fill=col)
    d.rectangle([x - h * 0.03, base - h * 0.12, x + h * 0.03, base], fill=(90, 64, 48))


@lru_cache(maxsize=16)
def background(scene: str) -> Image.Image:
    """Background 15% larger than the frame, so the camera can push in."""
    bw, bh = int(W * 1.15) * SS, int(H * 1.15) * SS
    if scene == "mind":
        img = _gradient((bw, bh), (16, 20, 44), (36, 28, 70))
        glow = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(glow).ellipse([bw * 0.1, bh * 0.15, bw * 0.9, bh * 0.65], fill=90)
        glow = glow.filter(ImageFilter.GaussianBlur(160))
        img.paste((90, 70, 170), (0, 0), glow)
        d = ImageDraw.Draw(img)
        rnd = random.Random(3)
        for _ in range(90):  # tiny "neurons"
            x, y = rnd.uniform(0, bw), rnd.uniform(0, bh)
            r = rnd.uniform(2, 5) * SS
            d.ellipse([x - r, y - r, x + r, y + r], fill=(120, 110, 200))
        return _down(img)
    if scene == "reef":
        return _down(_reef(bw, bh))
    if scene == "lab":
        return _down(_lab(bw, bh))
    if scene in ("park_day", "park_dark", "park_frozen"):
        return _down(_park(bw, bh, scene != "park_day", scene == "park_frozen"))
    if scene == "space":
        return _down(_space(bw, bh))
    if scene == "ocean_cut":
        return _down(_ocean_cut(bw, bh))
    if scene == "cave":
        return _down(_cave(bw, bh))
    if scene in ("home_day", "home_night"):
        return _down(_home(bw, bh, scene == "home_night"))
    if scene == "clinic":
        return _down(_clinic(bw, bh))
    if scene == "rooftop_dawn":
        return _down(_rooftop(bw, bh))
    if scene == "street_night":
        return _down(_street(bw, bh))

    p = PALETTES[scene]
    img = _gradient((bw, bh), *p["sky"])
    d = ImageDraw.Draw(img)
    rnd = random.Random(7)
    if p["dark"]:
        for _ in range(140):
            x, y = rnd.uniform(0, bw), rnd.uniform(0, bh * 0.45)
            r = rnd.uniform(1.5, 4) * SS
            d.ellipse([x - r, y - r, x + r, y + r], fill=(230, 236, 255))
        d.ellipse([bw * 0.72, bh * 0.08, bw * 0.84, bh * 0.08 + bw * 0.12], fill=(244, 240, 220))
    elif scene == "spring":
        d.ellipse([bw * 0.62, bh * 0.16, bw * 0.86, bh * 0.16 + bw * 0.24], fill=(255, 244, 200))
    horizon = bh * 0.5
    for i, col in enumerate((p["hill2"], p["hill"])):
        pts = [(0, bh)]
        for k in range(0, 41):
            x = bw * k / 40
            y = horizon - 120 * SS + i * 70 * SS - math.sin(k * 0.45 + i * 2) * 60 * SS - math.sin(k * 0.17) * 40 * SS
            pts.append((x, y))
        pts.append((bw, bh))
        d.polygon(pts, fill=col)
    tree = (70, 110, 96) if not p["dark"] else (28, 40, 60)
    if scene == "spring":
        tree = (64, 120, 78)
    for k in range(26):
        x = bw * (k + rnd.random() * 0.5) / 26
        _pine(d, x, horizon + 30 * SS + rnd.uniform(-10, 20) * SS, rnd.uniform(120, 200) * SS, tree)
    # river / ice band
    d.rectangle([0, horizon + 40 * SS, bw, horizon + 300 * SS], fill=p["ice"])
    if scene in ("ship_day", "ship_night", "spring"):
        _ship(d, bw * 0.3, horizon + 210 * SS, 1.0 * SS, p["hull"], scene == "spring", p["dark"])
        _ship(d, bw * 0.75, horizon + 170 * SS, 0.7 * SS, p["hull"], scene == "spring", p["dark"])
    if scene == "village":
        bark = (150, 120, 92)
        _longhouse(d, bw * 0.05, horizon + 230 * SS, 420 * SS, 190 * SS, bark)
        _longhouse(d, bw * 0.55, horizon + 200 * SS, 380 * SS, 160 * SS, _lerp(bark, (255, 255, 255), 0.1))
        # palisade
        for k in range(60):
            x = bw * k / 60
            d.rectangle([x, horizon + 150 * SS, x + 12 * SS, horizon + 250 * SS], fill=(132, 100, 74))
            d.polygon([(x, horizon + 150 * SS), (x + 6 * SS, horizon + 132 * SS), (x + 12 * SS, horizon + 150 * SS)], fill=(132, 100, 74))
    d.rectangle([0, horizon + 300 * SS, bw, bh], fill=p["ground"])
    if scene in ("ship_day", "ship_night", "village"):  # snow drifts
        drift = _lerp(p["ground"], (255, 255, 255), 0.4)
        for k in range(8):
            x = bw * k / 7
            d.ellipse([x - 260 * SS, horizon + 330 * SS, x + 260 * SS, horizon + 470 * SS], fill=drift)
    return _down(img)


def fire(t: float) -> Image.Image:
    """Campfire with a cooking pot, flicker driven by time t."""
    s = 300 * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, base = s / 2, s * 0.92
    for i, col in enumerate(((240, 110, 40), (255, 170, 60), (255, 230, 140))):
        f = 1 - i * 0.28
        wob = math.sin(t * 9 + i) * 10 * SS
        h = (150 + math.sin(t * 13 + i * 2) * 14) * SS * f
        d.polygon([(cx - 70 * SS * f, base - 30 * SS), (cx + wob, base - 30 * SS - h), (cx + 70 * SS * f, base - 30 * SS)], fill=col)
    for a in (-0.4, 0.4):
        d.line([(cx - 90 * SS, base - 10 * SS - a * 40 * SS), (cx + 90 * SS, base - 10 * SS + a * 40 * SS)], fill=(110, 72, 46), width=18 * SS)
    # pot on a tripod
    d.line([(cx - 110 * SS, base), (cx, base - 260 * SS)], fill=(80, 60, 44), width=8 * SS)
    d.line([(cx + 110 * SS, base), (cx, base - 260 * SS)], fill=(80, 60, 44), width=8 * SS)
    d.line([(cx, base - 260 * SS), (cx, base - 190 * SS)], fill=(60, 50, 40), width=4 * SS)
    d.chord([cx - 70 * SS, base - 220 * SS, cx + 70 * SS, base - 110 * SS], 0, 180, fill=(54, 54, 60))
    d.rectangle([cx - 70 * SS, base - 168 * SS, cx + 70 * SS, base - 162 * SS], fill=(54, 54, 60))
    for k in range(3):  # steam
        y = base - 230 * SS - ((t * 60 + k * 30) % 90) * SS
        d.ellipse([cx - 20 * SS + k * 18 * SS, y - 12 * SS, cx + k * 18 * SS, y + 12 * SS], fill=(255, 255, 255, 120))
    return _down(img)


# ---------------------------------------------------------------- characters

LOOKS = {
    # coat, hat, skin, hat style, hair
    "hero": dict(coat=(36, 150, 140), hat=(240, 110, 40), skin=(242, 200, 160), hat_style="toque", hair=None),
    "hero_shrimp": dict(coat=(36, 150, 140), hat=(240, 110, 40), skin=(242, 200, 160), hat_style="toque", hair=None),
    "scientist": dict(coat=(246, 248, 250), hat=None, skin=(214, 168, 130), hat_style=None, hair=(70, 50, 40)),
    "sailor": dict(coat=(120, 92, 70), hat=(70, 80, 100), skin=(236, 196, 160), hat_style="cap", hair=None),
    "sailor2": dict(coat=(90, 96, 112), hat=(150, 50, 50), skin=(222, 178, 140), hat_style="cap", hair=None),
    "guide": dict(coat=(176, 128, 84), hat=None, skin=(196, 140, 100), hat_style=None, hair=(40, 30, 26)),
    "woman": dict(coat=(160, 112, 76), hat=None, skin=(200, 146, 106), hat_style=None, hair=(36, 28, 24), long_hair=True),
    "doctor": dict(coat=(244, 248, 252), hat=None, skin=(150, 104, 76), hat_style=None, hair=(30, 24, 22)),
    "mom": dict(coat=(150, 90, 150), hat=None, skin=(236, 196, 164), hat_style=None, hair=(110, 70, 50), long_hair=True),
    "friend": dict(coat=(214, 64, 64), hat=(40, 44, 60), skin=(196, 140, 100), hat_style="cap", hair=None),
    "woman2": dict(coat=(186, 140, 96), hat=None, skin=(190, 136, 98), hat_style=None, hair=(44, 32, 26), long_hair=True),
}


@lru_cache(maxsize=256)
def character(who: str, mood: str, blink: bool = False, scale: float = 1.0) -> Image.Image:
    """Chunky round character, ~520px tall at scale 1. Feet at bottom centre."""
    L = LOOKS[who]
    cw, ch = 440 * SS, 560 * SS
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cw / 2
    skin = L["skin"]
    if mood == "sick":
        skin = _lerp(skin, (190, 210, 170), 0.45)
    if mood == "cold":
        skin = _lerp(skin, (200, 214, 240), 0.35)
    coat = L["coat"]
    # body
    d.rounded_rectangle([cx - 130 * SS, 280 * SS, cx + 130 * SS, 560 * SS], radius=110 * SS, fill=coat)
    if L.get("long_hair"):  # two side strands falling onto the shoulders
        for sx in (-1, 1):
            x0 = cx + sx * 128 * SS
            d.rounded_rectangle([min(x0, x0 - sx * 70 * SS), 150 * SS, max(x0, x0 - sx * 70 * SS), 400 * SS], radius=34 * SS, fill=L["hair"])
    if who in ("guide", "woman", "woman2"):  # fringe trim on hide clothing
        trim = _lerp(coat, (255, 240, 210), 0.35)
        for k in range(9):
            x = cx - 100 * SS + k * 25 * SS
            d.line([(x, 470 * SS), (x, 500 * SS)], fill=trim, width=5 * SS)
        d.line([(cx - 110 * SS, 466 * SS), (cx + 110 * SS, 466 * SS)], fill=trim, width=6 * SS)
    if who in ("hero", "hero_shrimp"):  # zipper + collar
        d.line([(cx, 300 * SS), (cx, 550 * SS)], fill=_lerp(coat, (0, 0, 0), 0.25), width=6 * SS)
    # head
    hr = 120 * SS
    hy = 190 * SS
    d.ellipse([cx - hr, hy - hr, cx + hr, hy + hr], fill=skin)
    # hair / hats
    if L["hair"] is not None:
        d.chord([cx - hr, hy - hr, cx + hr, hy + hr * 0.6], 180, 360, fill=L["hair"])
    if L["hat_style"] == "toque":
        d.chord([cx - hr * 1.02, hy - hr * 1.15, cx + hr * 1.02, hy + hr * 0.5], 180, 360, fill=L["hat"])
        d.rounded_rectangle([cx - hr * 1.06, hy - hr * 0.42, cx + hr * 1.06, hy - hr * 0.12], radius=14 * SS,
                            fill=_lerp(L["hat"], (255, 255, 255), 0.25))
        d.ellipse([cx - 32 * SS, hy - hr * 1.15 - 40 * SS, cx + 32 * SS, hy - hr * 1.15 + 20 * SS], fill=(255, 236, 210))
    elif L["hat_style"] == "cap":
        d.chord([cx - hr * 1.0, hy - hr * 1.05, cx + hr * 1.0, hy + hr * 0.4], 180, 360, fill=L["hat"])
    # face
    ex, ey, er = 44 * SS, hy + 10 * SS, 22 * SS
    ink = (34, 30, 40)
    if who == "scientist":
        for sx in (-1, 1):
            d.ellipse([cx + sx * ex - 36 * SS, ey - 32 * SS, cx + sx * ex + 36 * SS, ey + 32 * SS], outline=(40, 40, 50), width=6 * SS)
        d.line([(cx - ex + 36 * SS, ey), (cx + ex - 36 * SS, ey)], fill=(40, 40, 50), width=6 * SS)
    if who == "doctor":  # stethoscope
        d.arc([cx - 70 * SS, 290 * SS, cx + 70 * SS, 430 * SS], 0, 180, fill=(60, 70, 90), width=8 * SS)
        d.ellipse([cx - 20 * SS, 420 * SS, cx + 20 * SS, 460 * SS], fill=(160, 170, 190))
    if who == "scientist":  # glasses + coat lapels
        d.line([(cx - 40 * SS, 300 * SS), (cx, 380 * SS), (cx + 40 * SS, 300 * SS)], fill=(190, 196, 206), width=8 * SS)
    for sx in (-1, 1):
        x = cx + sx * ex
        if who == "hero_shrimp":  # stalk eyes are drawn after, on a taller canvas
            continue
        if blink or mood in ("happy", "smug", "asleep"):
            if mood == "happy" and not blink:
                d.arc([x - er, ey - er * 0.6, x + er, ey + er * 1.2], 200, 340, fill=ink, width=7 * SS)
            else:
                d.line([(x - er, ey), (x + er, ey)], fill=ink, width=7 * SS)
        elif mood == "shock":
            d.ellipse([x - er * 1.3, ey - er * 1.3, x + er * 1.3, ey + er * 1.3], fill=(255, 255, 255), outline=ink, width=5 * SS)
            d.ellipse([x - er * 0.45, ey - er * 0.45, x + er * 0.45, ey + er * 0.45], fill=ink)
        else:
            d.ellipse([x - er * 0.75, ey - er, x + er * 0.75, ey + er], fill=ink)
            d.ellipse([x - er * 0.3, ey - er * 0.7, x + er * 0.05, ey - er * 0.3], fill=(255, 255, 255))
    # brows
    by = ey - 42 * SS
    if who == "hero_shrimp":
        pass
    elif mood in ("worried", "sick", "cold", "awkward"):
        d.line([(cx - ex - 24 * SS, by), (cx - ex + 20 * SS, by - 14 * SS)], fill=ink, width=7 * SS)
        d.line([(cx + ex - 20 * SS, by - 14 * SS), (cx + ex + 24 * SS, by)], fill=ink, width=7 * SS)
    elif mood == "smug":
        d.line([(cx - ex - 24 * SS, by - 14 * SS), (cx - ex + 22 * SS, by)], fill=ink, width=7 * SS)
        d.line([(cx + ex - 22 * SS, by - 6 * SS), (cx + ex + 24 * SS, by - 16 * SS)], fill=ink, width=7 * SS)
    # mouth
    my = hy + 66 * SS
    if mood == "happy":
        d.chord([cx - 34 * SS, my - 20 * SS, cx + 34 * SS, my + 28 * SS], 0, 180, fill=ink)
    elif mood == "shock":
        d.ellipse([cx - 16 * SS, my - 14 * SS, cx + 16 * SS, my + 22 * SS], fill=ink)
    elif mood == "smug":
        d.arc([cx - 30 * SS, my - 26 * SS, cx + 36 * SS, my + 10 * SS], 20, 150, fill=ink, width=7 * SS)
    elif mood in ("worried", "sick", "cold"):
        d.arc([cx - 26 * SS, my, cx + 26 * SS, my + 30 * SS], 200, 340, fill=ink, width=7 * SS)
    elif mood == "awkward":
        d.line([(cx - 28 * SS, my + 6 * SS), (cx - 8 * SS, my), (cx + 10 * SS, my + 8 * SS), (cx + 28 * SS, my + 2 * SS)], fill=ink, width=6 * SS)
    elif mood == "asleep":  # little open mouth + floating z's
        d.ellipse([cx - 10 * SS, my - 4 * SS, cx + 10 * SS, my + 14 * SS], fill=ink)
        for k, (zx, zy, zs) in enumerate(((112, -100, 40), (150, -140, 50), (185, -172, 60))):
            d.text((cx + zx * SS, hy + zy * SS), "z", font=font(zs * SS), fill=(250, 250, 255), anchor="mm",
                   stroke_width=4 * SS, stroke_fill=ink)
    else:  # calm / flat
        d.line([(cx - 22 * SS, my + 6 * SS), (cx + 22 * SS, my + 6 * SS)], fill=ink, width=7 * SS)
    if mood == "awkward":  # sweat drop
        d.ellipse([cx + hr * 0.75, hy - 40 * SS, cx + hr * 0.75 + 26 * SS, hy - 4 * SS], fill=(150, 210, 250))
    if mood == "cold":  # breath puff
        d.ellipse([cx + 60 * SS, my - 10 * SS, cx + 110 * SS, my + 30 * SS], fill=(255, 255, 255, 170))
    if mood in ("happy", "calm", "shock", "smug", "flat", "awkward"):  # rosy cheeks
        blush = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        bd = ImageDraw.Draw(blush)
        for sx in (-1, 1):
            x = cx + sx * 74 * SS
            bd.ellipse([x - 24 * SS, ey + 30 * SS, x + 24 * SS, ey + 50 * SS], fill=(255, 120, 120, 80))
        img.alpha_composite(blush)
        d = ImageDraw.Draw(img)
    if who != "hero_shrimp":
        _arms(d, cx, L, mood, skin)
    if who == "hero_shrimp":  # eyes on stalks poking out of the toque
        oy = 170 * SS
        big = Image.new("RGBA", (cw, ch + oy), (0, 0, 0, 0))
        bd = ImageDraw.Draw(big)
        top = hy - hr + oy
        for sx in (-1, 1):
            tipx, tipy = cx + sx * 80 * SS, top - 120 * SS
            bd.line([(cx + sx * 30 * SS, top + 30 * SS), (tipx, tipy)], fill=(60, 190, 120), width=14 * SS)
            bd.ellipse([tipx - 44 * SS, tipy - 32 * SS, tipx + 44 * SS, tipy + 32 * SS], fill=(60, 70, 90))
            if not blink:
                bd.rectangle([tipx - 44 * SS, tipy - 6 * SS, tipx + 44 * SS, tipy + 6 * SS], fill=(250, 220, 90))
                bd.ellipse([tipx - 12 * SS, tipy - 22 * SS, tipx + 4 * SS, tipy - 8 * SS], fill=(255, 255, 255))
            else:
                bd.line([(tipx - 40 * SS, tipy), (tipx + 40 * SS, tipy)], fill=(250, 220, 90), width=6 * SS)
        big.alpha_composite(img, (0, oy))
        img = big
    out = _shade(_down(img))
    if scale != 1.0:
        out = out.resize((int(out.width * scale), int(out.height * scale)), Image.LANCZOS)
    return out


ARM_POSES = {  # hand positions relative to (cx, shoulder) in 1x units, (left, right)
    "shock": ((-150, -120), (150, -120)),
    "happy": ((-150, 140), (175, -150)),
    "worried": ((-36, 110), (36, 110)),
    "cold": ((70, 70), (-70, 70)),
}


def _arms(d, cx, L, mood, skin):
    """Stubby arms with mittens; the pose follows the mood."""
    sy = 335 * SS
    coat = _lerp(L["coat"], (0, 0, 0), 0.12)
    edge = _lerp(L["coat"], (0, 0, 0), 0.45)
    hand = L["hat"] if L.get("hat_style") == "toque" else skin
    pose = ARM_POSES.get(mood, ((-160, 150), (160, 150)))
    for sx, (hx, hy) in zip((-1, 1), pose):
        a = (cx + sx * 112 * SS, sy)
        b = (cx + hx * SS, sy + hy * SS)
        d.line([a, b], fill=edge, width=54 * SS)
        for p in (a, b):
            d.ellipse([p[0] - 27 * SS, p[1] - 27 * SS, p[0] + 27 * SS, p[1] + 27 * SS], fill=edge)
        d.line([a, b], fill=coat, width=42 * SS)
        d.ellipse([a[0] - 21 * SS, a[1] - 21 * SS, a[0] + 21 * SS, a[1] + 21 * SS], fill=coat)
        d.ellipse([b[0] - 32 * SS, b[1] - 32 * SS, b[0] + 32 * SS, b[1] + 32 * SS], fill=edge)
        d.ellipse([b[0] - 26 * SS, b[1] - 26 * SS, b[0] + 26 * SS, b[1] + 26 * SS], fill=hand)


def _shift(mask, dx, dy):
    out = Image.new("L", mask.size, 0)
    out.paste(mask, (dx, dy))
    return out


def _shade(img: Image.Image) -> Image.Image:
    """Cartoon finish: soft shadow on the lower right, rim light on the upper left, dark outline."""
    a = img.getchannel("A")
    shadow = ImageChops.subtract(a, _shift(a, -16, -10)).filter(ImageFilter.GaussianBlur(6))
    shadow = ImageChops.multiply(shadow, a).point(lambda v: int(v * 0.30))
    light = ImageChops.subtract(a, _shift(a, 8, 8)).filter(ImageFilter.GaussianBlur(3))
    light = ImageChops.multiply(light, a).point(lambda v: int(v * 0.22))
    img = img.copy()
    img.paste((24, 14, 44), (0, 0), shadow)
    img.paste((255, 255, 255), (0, 0), light)
    img.putalpha(a)
    pad = 6
    big = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    big.paste(img, (pad, pad))
    ring = big.getchannel("A").filter(ImageFilter.MaxFilter(7))
    out = Image.new("RGBA", big.size, (28, 22, 40, 0))
    out.putalpha(ring)
    out.alpha_composite(big)
    return out


# ---------------------------------------------------------------- overlays

def pill(text: str, color: str, size: int = 46) -> Image.Image:
    fills = {"gold": ((255, 196, 54), (40, 26, 0)), "red": ((222, 54, 54), (255, 255, 255)),
             "dark": ((22, 22, 30), (255, 255, 255)), "kicker": ((255, 255, 255), (22, 22, 30))}
    bg, fg = fills.get(color, fills["dark"])
    f = font(size * SS)
    tw = f.getlength(text)
    pw, ph = int(tw + 70 * SS), int(size * SS * 1.9)
    img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2, fill=bg)
    d.text((pw / 2, ph / 2), text, font=f, fill=fg, anchor="mm")
    return _down(img)


def card(title: str, rows, shown: int, alert=None) -> Image.Image:
    """Checklist card drawn like a sticky note pinned to a corkboard."""
    cw = 860 * SS
    row_h = 104 * SS
    n_alert = 1 if alert else 0
    ch = int(150 * SS + row_h * len(rows) + n_alert * 200 * SS + 30 * SS)
    img = Image.new("RGBA", (cw + 30 * SS, ch + 30 * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([18 * SS, 22 * SS, cw + 18 * SS, ch + 22 * SS], radius=26 * SS, fill=(0, 0, 0, 90))
    d.rounded_rectangle([0, 0, cw, ch], radius=26 * SS, fill=(252, 246, 228))
    d.rounded_rectangle([0, 0, cw, 120 * SS], radius=26 * SS, fill=(255, 196, 54))
    d.rectangle([0, 80 * SS, cw, 120 * SS], fill=(255, 196, 54))
    d.text((44 * SS, 60 * SS), title, font=font(52 * SS), fill=(40, 26, 0), anchor="lm")
    d.ellipse([cw - 80 * SS, 34 * SS, cw - 30 * SS, 84 * SS], fill=(222, 54, 54))  # pin
    for i, row in enumerate(rows[:shown]):
        txt, tag = row[0], row[1]
        y = 150 * SS + i * row_h
        d.rounded_rectangle([30 * SS, y, cw - 30 * SS, y + row_h - 18 * SS], radius=18 * SS, fill=(255, 255, 255))
        d.text((60 * SS, y + (row_h - 18 * SS) / 2), txt, font=font(42 * SS, "semi"), fill=(30, 30, 40), anchor="lm")
        good = row[2] == "good" if len(row) > 2 else tag.upper() in ("YES", "KNOWN", "OK")
        tcol = (30, 150, 90) if good else (210, 50, 50)
        d.text((cw - 60 * SS, y + (row_h - 18 * SS) / 2), tag.upper(), font=font(36 * SS), fill=tcol, anchor="rm")
    if alert and shown > len(rows):
        y = 150 * SS + len(rows) * row_h + 10 * SS
        d.rounded_rectangle([30 * SS, y, cw - 30 * SS, y + 180 * SS], radius=20 * SS, fill=(255, 232, 232), outline=(222, 54, 54), width=5 * SS)
        d.text((64 * SS, y + 56 * SS), alert[0], font=font(44 * SS), fill=(190, 30, 30), anchor="lm")
        d.text((64 * SS, y + 124 * SS), alert[1], font=font(36 * SS, "semi"), fill=(120, 40, 40), anchor="lm")
    return _down(img)


ORBIT_ICONS = ["+", "Rx", "C", "♥", "DNA", "⚕"]


def orbit(t: float) -> Image.Image:
    """Ring of knowledge bubbles circling the hero in the hook shot."""
    s = 900 * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    d.ellipse([c - 330 * SS, c - 330 * SS, c + 330 * SS, c + 330 * SS], outline=(255, 255, 255, 140), width=5 * SS)
    labels = ["VITAMINS", "GERMS", "VACCINES", "SURGERY", "DNA", "ANTIBIOTICS"]
    cols = [(255, 196, 54), (90, 200, 160), (120, 160, 255), (255, 120, 120), (200, 140, 255), (255, 160, 80)]
    for i, (lab, col) in enumerate(zip(labels, cols)):
        a = t * 0.6 + i * math.tau / len(labels)
        x, y = c + math.cos(a) * 330 * SS, c + math.sin(a) * 330 * SS
        f = font(30 * SS)
        tw = f.getlength(lab)
        d.rounded_rectangle([x - tw / 2 - 22 * SS, y - 34 * SS, x + tw / 2 + 22 * SS, y + 34 * SS], radius=34 * SS, fill=col)
        d.text((x, y), lab, font=f, fill=(20, 20, 30), anchor="mm")
    return _down(img)


# ---------------------------------------------------------------- science scenes

def _reef(bw, bh):
    img = _gradient((bw, bh), (40, 150, 200), (8, 40, 90))
    rays = Image.new("L", (bw, bh), 0)
    rd = ImageDraw.Draw(rays)
    for k in range(7):
        x = bw * (0.05 + k * 0.15)
        rd.polygon([(x, 0), (x + 90 * SS, 0), (x + 380 * SS, bh * 0.75), (x + 200 * SS, bh * 0.75)], fill=40)
    rays = rays.filter(ImageFilter.GaussianBlur(30 * SS))
    img.paste((200, 240, 255), (0, 0), rays)
    d = ImageDraw.Draw(img)
    rnd = random.Random(11)
    floor = bh * 0.68
    pts = [(0, bh)] + [(bw * k / 30, floor + math.sin(k * 0.7) * 30 * SS) for k in range(31)] + [(bw, bh)]
    d.polygon(pts, fill=(226, 196, 140))
    for k in range(14):  # coral
        x = rnd.uniform(0, bw)
        col = rnd.choice([(250, 110, 120), (255, 170, 80), (180, 110, 220), (90, 200, 170)])
        h = rnd.uniform(140, 300) * SS
        base = floor + rnd.uniform(-10, 40) * SS
        for b in range(5):
            ang = -math.pi / 2 + (b - 2) * 0.35
            x2, y2 = x + math.cos(ang) * h * 0.8, base + math.sin(ang) * h
            d.line([(x, base), (x2, y2)], fill=col, width=int(26 * SS))
            d.ellipse([x2 - 18 * SS, y2 - 18 * SS, x2 + 18 * SS, y2 + 18 * SS], fill=col)
    for k in range(10):  # seaweed
        x = rnd.uniform(0, bw)
        base = floor + rnd.uniform(0, 60) * SS
        pts = [(x + math.sin(i * 0.8) * 26 * SS, base - i * 40 * SS) for i in range(9)]
        d.line(pts, fill=(50, 140, 90), width=int(20 * SS), joint="curve")
    for k in range(40):  # bubbles
        x, y = rnd.uniform(0, bw), rnd.uniform(0, floor)
        r = rnd.uniform(5, 16) * SS
        d.ellipse([x - r, y - r, x + r, y + r], outline=(220, 245, 255), width=int(3 * SS))
    return img


def _lab(bw, bh):
    img = _gradient((bw, bh), (232, 238, 244), (206, 216, 228))
    d = ImageDraw.Draw(img)
    floor = bh * 0.66
    d.rectangle([0, floor, bw, bh], fill=(176, 188, 204))
    for k in range(12):  # floor tiles
        x = bw * k / 12
        d.line([(x, floor), (x - 200 * SS, bh)], fill=(160, 172, 190), width=int(4 * SS))
    # wall shelves with flasks
    for row in (0.34, 0.46):
        y = bh * row
        d.rectangle([bw * 0.08, y, bw * 0.92, y + 16 * SS], fill=(150, 160, 176))
        rnd = random.Random(int(row * 100))
        for k in range(9):
            x = bw * (0.12 + k * 0.09)
            col = rnd.choice([(120, 200, 255), (255, 140, 160), (160, 230, 150), (255, 210, 110)])
            d.rectangle([x - 14 * SS, y - 90 * SS, x + 14 * SS, y - 50 * SS], fill=(214, 226, 236))
            d.polygon([(x - 14 * SS, y - 50 * SS), (x + 14 * SS, y - 50 * SS), (x + 44 * SS, y), (x - 44 * SS, y)], fill=col)
    # bench
    d.rectangle([bw * 0.04, floor + 40 * SS, bw * 0.96, floor + 80 * SS], fill=(90, 100, 120))
    return img


def lamps(left_col, right_col, t: float) -> Image.Image:
    """Two light boxes on a stand, for the colour test."""
    s = 2
    w, h = 900 * s, 360 * s
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, col in enumerate((left_col, right_col)):
        cx = w * (0.27 + i * 0.46)
        glow = Image.new("L", (w, h), 0)
        ImageDraw.Draw(glow).ellipse([cx - 170 * s, 20 * s, cx + 170 * s, 300 * s], fill=int(110 + 30 * math.sin(t * 4 + i)))
        glow = glow.filter(ImageFilter.GaussianBlur(40 * s))
        layer = Image.new("RGBA", (w, h), col + (0,))
        layer.putalpha(glow)
        img.alpha_composite(layer)
        d.rounded_rectangle([cx - 100 * s, 70 * s, cx + 100 * s, 250 * s], radius=30 * s, fill=(40, 44, 56))
        d.ellipse([cx - 70 * s, 90 * s, cx + 70 * s, 230 * s], fill=col)
        d.rectangle([cx - 12 * s, 250 * s, cx + 12 * s, 340 * s], fill=(70, 76, 90))
    return img.resize((w // s, h // s), Image.LANCZOS)


@lru_cache(maxsize=8)
def shrimp(flip: bool = False) -> Image.Image:
    """A cartoon mantis shrimp: striped body, stalked eyes, folded punching club."""
    w, h = 640 * SS, 360 * SS
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cols = [(60, 190, 120), (40, 160, 200), (250, 120, 60), (230, 70, 90), (250, 200, 60), (140, 90, 220)]
    for k in range(6):  # body segments, tail on the left
        x = 120 * SS + k * 70 * SS
        r = (60 + k * 6) * SS
        d.ellipse([x - r, 200 * SS - r * 0.8, x + r, 200 * SS + r * 0.8], fill=cols[k])
    d.polygon([(40 * SS, 200 * SS), (110 * SS, 150 * SS), (110 * SS, 250 * SS)], fill=(250, 120, 60))  # tail fan
    for k in range(5):  # legs
        x = 170 * SS + k * 60 * SS
        d.line([(x, 250 * SS), (x - 20 * SS, 300 * SS)], fill=(230, 70, 90), width=int(10 * SS))
    # club
    d.line([(520 * SS, 220 * SS), (560 * SS, 290 * SS), (600 * SS, 250 * SS)], fill=(240, 90, 110), width=int(22 * SS), joint="curve")
    d.ellipse([580 * SS, 228 * SS, 625 * SS, 273 * SS], fill=(255, 140, 150))
    # eyes on stalks
    for ex, ey in ((500 * SS, 70 * SS), (560 * SS, 60 * SS)):
        d.line([(500 * SS, 170 * SS), (ex, ey + 30 * SS)], fill=(60, 190, 120), width=int(14 * SS))
        d.ellipse([ex - 34 * SS, ey - 26 * SS, ex + 34 * SS, ey + 26 * SS], fill=(60, 70, 90))
        d.rectangle([ex - 34 * SS, ey - 5 * SS, ex + 34 * SS, ey + 5 * SS], fill=(250, 220, 90))
        d.ellipse([ex - 8 * SS, ey - 14 * SS, ex + 4 * SS, ey - 4 * SS], fill=(255, 255, 255))
    out = _down(img)
    return out.transpose(Image.FLIP_LEFT_RIGHT) if flip else out


# ---------------------------------------------------------------- action props

def burst(text: str) -> Image.Image:
    """Comic impact star with a word in it."""
    s = 520 * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    for rad, col in ((250, (255, 255, 255)), (215, (255, 205, 40)), (170, (255, 120, 40))):
        pts = []
        for k in range(28):
            r = rad * SS * (1.0 if k % 2 == 0 else 0.62)
            a = k * math.tau / 28
            pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
        d.polygon(pts, fill=col)
    d.text((c, c), text, font=font(96 * SS), fill=(255, 255, 255), anchor="mm", stroke_width=10 * SS, stroke_fill=(30, 20, 20))
    return _down(img)


@lru_cache(maxsize=16)
def prop(kind: str, broken: bool) -> Image.Image:
    """Things to punch: vending machine, brick wall, aquarium. Bottom centre = floor contact."""
    w, h = 360 * SS, 640 * SS
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    crack = (30, 30, 40)
    if kind == "vending":
        d.rounded_rectangle([0, 0, w, h], radius=24 * SS, fill=(220, 50, 60))
        d.rectangle([30 * SS, 40 * SS, 240 * SS, 470 * SS], fill=(200, 230, 245))
        rnd = random.Random(2)
        for r in range(5):
            for c in range(3):
                x, y = 50 * SS + c * 66 * SS, 60 * SS + r * 82 * SS
                d.rounded_rectangle([x, y, x + 46 * SS, y + 60 * SS], radius=8 * SS,
                                    fill=rnd.choice([(255, 180, 60), (90, 180, 255), (120, 220, 120), (250, 110, 160)]))
        d.rectangle([260 * SS, 120 * SS, 330 * SS, 300 * SS], fill=(60, 60, 70))
        d.rectangle([60 * SS, 520 * SS, 220 * SS, 580 * SS], fill=(40, 40, 50))
        if broken:
            d.polygon([(20 * SS, 40 * SS), (240 * SS, 30 * SS), (250 * SS, 470 * SS), (30 * SS, 480 * SS)], fill=(170, 200, 215))
            for a in range(9):
                ang = a * math.tau / 9
                d.line([(135 * SS, 250 * SS), (135 * SS + math.cos(ang) * 200 * SS, 250 * SS + math.sin(ang) * 230 * SS)], fill=crack, width=5 * SS)
            img = img.rotate(-6, resample=Image.BICUBIC, center=(w / 2, h))
    elif kind == "wall":
        d.rectangle([0, 0, w, h], fill=(180, 90, 70))
        for r in range(16):
            y = r * 40 * SS
            off = 0 if r % 2 == 0 else 45 * SS
            d.line([(0, y), (w, y)], fill=(230, 220, 210), width=5 * SS)
            for c in range(-1, 5):
                x = c * 90 * SS + off
                d.line([(x, y), (x, y + 40 * SS)], fill=(230, 220, 210), width=5 * SS)
        if broken:
            for a in range(7):
                ang = a * math.tau / 7 + 0.3
                d.line([(180 * SS, 330 * SS), (180 * SS + math.cos(ang) * 120 * SS, 330 * SS + math.sin(ang) * 140 * SS)], fill=crack, width=6 * SS)
    elif kind == "tank":
        h2 = 420 * SS
        top = h - h2
        d.rectangle([0, top, w, h], fill=(120, 200, 240, 180))
        d.rectangle([0, top, w, top + 30 * SS], fill=(90, 170, 220, 200))
        d.rectangle([0, h - 40 * SS, w, h], fill=(226, 196, 140))
        d.rectangle([0, top, w, h], outline=(230, 245, 255), width=10 * SS)
        if broken:
            for a in range(10):
                ang = a * math.tau / 10
                d.line([(110 * SS, top + 200 * SS), (110 * SS + math.cos(ang) * 260 * SS, top + 200 * SS + math.sin(ang) * 200 * SS)], fill=(255, 255, 255), width=5 * SS)
            for k in range(14):  # water spray
                x = -40 * SS + k * 8 * SS
                d.ellipse([x, top + 180 * SS + k * 12 * SS, x + 26 * SS, top + 206 * SS + k * 12 * SS], fill=(120, 200, 240))
    return _down(img)


def club_arm(length: float) -> Image.Image:
    """Pink striking club on an arm, pointing right. length in px (output scale)."""
    L = int(max(60, length)) * SS
    h = 150 * SS
    img = Image.new("RGBA", (L + 140 * SS, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, h / 2 - 24 * SS, L, h / 2 + 24 * SS], radius=24 * SS, fill=(36, 150, 140))
    d.ellipse([L - 20 * SS, 5 * SS, L + 130 * SS, h - 5 * SS], fill=(255, 120, 150))
    d.ellipse([L + 30 * SS, 30 * SS, L + 80 * SS, 70 * SS], fill=(255, 200, 215))
    return _down(img)


def speedlines(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rnd = random.Random(int(t * 20))
    for _ in range(46):
        a = rnd.uniform(0, math.tau)
        r0 = rnd.uniform(380, 560)
        cx, cy = W / 2, H * 0.62
        d.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0), (cx + math.cos(a) * 1500, cy + math.sin(a) * 1500)],
               fill=(255, 255, 255, 150), width=rnd.randint(3, 9))
    return img


# ---------------------------------------------------------------- story scenes: the Sun vanishes

def _skyline(d, bw, base, col, windows=None, seed=5):
    rnd = random.Random(seed)
    x = 0
    while x < bw:
        w = rnd.uniform(90, 200) * SS
        h = rnd.uniform(180, 520) * SS
        d.rectangle([x, base - h, x + w, base], fill=col)
        if windows:
            for wy in range(int(base - h + 30 * SS), int(base - 30 * SS), int(46 * SS)):
                for wx in range(int(x + 18 * SS), int(x + w - 30 * SS), int(40 * SS)):
                    if rnd.random() < 0.55:
                        d.rectangle([wx, wy, wx + 18 * SS, wy + 24 * SS], fill=windows)
        x += w + rnd.uniform(6, 30) * SS


def _park(bw, bh, dark: bool, frozen: bool = False):
    if frozen:
        img = _gradient((bw, bh), (4, 6, 16), (20, 28, 48))
    elif dark:
        img = _gradient((bw, bh), (2, 3, 10), (12, 16, 34))
    else:
        img = _gradient((bw, bh), (110, 180, 245), (210, 232, 250))
    d = ImageDraw.Draw(img)
    rnd = random.Random(21)
    if dark or frozen:
        for _ in range(420):
            x, y = rnd.uniform(0, bw), rnd.uniform(0, bh * 0.55)
            r = rnd.uniform(1.2, 4.2) * SS
            d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 240, 255))
        # the Milky Way smear
        band = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(band).polygon([(0, bh * 0.35), (bw, bh * 0.05), (bw, bh * 0.15), (0, bh * 0.45)], fill=45)
        band = band.filter(ImageFilter.GaussianBlur(60 * SS))
        img.paste((200, 200, 255), (0, 0), band)
        d = ImageDraw.Draw(img)
    else:
        pass  # the Sun itself is drawn per frame (art.sun_disc) so it can vanish
    horizon = bh * 0.56
    city = (150, 176, 206) if not (dark or frozen) else (16, 20, 34)
    _skyline(d, bw, horizon + 40 * SS, city, windows=(255, 220, 120) if dark and not frozen else None)
    ground = (110, 180, 96) if not (dark or frozen) else (20, 34, 30)
    if frozen:
        ground = (190, 210, 230)
    d.rectangle([0, horizon + 40 * SS, bw, bh], fill=ground)
    tree = (60, 140, 80) if not (dark or frozen) else (10, 22, 20)
    if frozen:
        tree = (120, 140, 160)
    for k in range(7):
        x = bw * (0.05 + k * 0.15) + rnd.uniform(-30, 30) * SS
        base = horizon + 120 * SS
        d.rectangle([x - 14 * SS, base - 120 * SS, x + 14 * SS, base], fill=(90, 64, 48) if not (dark or frozen) else (14, 16, 20))
        if frozen:  # bare branches + frost
            for b in range(5):
                ang = -math.pi / 2 + (b - 2) * 0.45
                d.line([(x, base - 100 * SS), (x + math.cos(ang) * 120 * SS, base - 100 * SS + math.sin(ang) * 140 * SS)], fill=tree, width=int(10 * SS))
        else:
            d.ellipse([x - 110 * SS, base - 330 * SS, x + 110 * SS, base - 100 * SS], fill=tree)
    # bench
    by = horizon + 300 * SS
    bench = (150, 100, 60) if not (dark or frozen) else (40, 34, 30)
    d.rectangle([bw * 0.62, by, bw * 0.92, by + 22 * SS], fill=bench)
    d.rectangle([bw * 0.62, by - 70 * SS, bw * 0.92, by - 50 * SS], fill=bench)
    if frozen:  # icicles on the bench, snow drifts
        for k in range(14):
            x = bw * 0.62 + k * 22 * SS
            d.polygon([(x, by + 22 * SS), (x + 10 * SS, by + 22 * SS), (x + 5 * SS, by + 70 * SS)], fill=(220, 240, 255))
        for k in range(8):
            x = bw * k / 7
            d.ellipse([x - 240 * SS, horizon + 260 * SS, x + 240 * SS, horizon + 420 * SS], fill=(220, 232, 245))
    return img


def _space(bw, bh):
    img = _gradient((bw, bh), (2, 2, 8), (8, 6, 20))
    d = ImageDraw.Draw(img)
    rnd = random.Random(33)
    for _ in range(600):
        x, y = rnd.uniform(0, bw), rnd.uniform(0, bh)
        r = rnd.uniform(1, 4) * SS
        c = rnd.choice([(255, 255, 255), (200, 220, 255), (255, 230, 200)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    return img


def _ocean_cut(bw, bh):
    img = _gradient((bw, bh), (14, 40, 70), (2, 6, 14))
    d = ImageDraw.Draw(img)
    # sky strip + ice lid
    d.rectangle([0, 0, bw, bh * 0.22], fill=(4, 6, 14))
    rnd = random.Random(4)
    for _ in range(120):
        x, y = rnd.uniform(0, bw), rnd.uniform(0, bh * 0.2)
        d.ellipse([x - 3 * SS, y - 3 * SS, x + 3 * SS, y + 3 * SS], fill=(230, 235, 255))
    pts = [(0, bh * 0.22)] + [(bw * k / 20, bh * 0.22 + rnd.uniform(-10, 10) * SS) for k in range(21)] + [(bw, bh * 0.3), (0, bh * 0.3)]
    d.polygon(pts, fill=(200, 226, 245))
    for k in range(30):  # cracks in the ice
        x = rnd.uniform(0, bw)
        d.line([(x, bh * 0.23), (x + rnd.uniform(-40, 40) * SS, bh * 0.29)], fill=(160, 196, 226), width=int(3 * SS))
    # sea floor with vents
    floor = bh * 0.86
    pts = [(0, bh)] + [(bw * k / 24, floor + math.sin(k * 0.9) * 26 * SS) for k in range(25)] + [(bw, bh)]
    d.polygon(pts, fill=(30, 26, 30))
    for vx in (0.3, 0.62, 0.85):
        x = bw * vx
        d.polygon([(x - 70 * SS, floor + 10 * SS), (x - 20 * SS, floor - 230 * SS), (x + 20 * SS, floor - 230 * SS), (x + 70 * SS, floor + 10 * SS)], fill=(54, 44, 46))
        glow = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(glow).ellipse([x - 150 * SS, floor - 340 * SS, x + 150 * SS, floor - 60 * SS], fill=120)
        glow = glow.filter(ImageFilter.GaussianBlur(40 * SS))
        img.paste((255, 120, 50), (0, 0), glow)
        d = ImageDraw.Draw(img)
        for k in range(18):  # bacterial mats / tube worms
            tx = x + rnd.uniform(-160, 160) * SS
            d.line([(tx, floor), (tx, floor - rnd.uniform(30, 90) * SS)], fill=(240, 240, 240), width=int(8 * SS))
            d.ellipse([tx - 9 * SS, floor - 100 * SS, tx + 9 * SS, floor - 80 * SS], fill=(230, 50, 60))
    return img


def _cave(bw, bh):
    img = _gradient((bw, bh), (24, 18, 16), (54, 40, 32))
    d = ImageDraw.Draw(img)
    rnd = random.Random(8)
    for k in range(18):  # stalactites
        x = rnd.uniform(0, bw)
        d.polygon([(x - 40 * SS, 0), (x + 40 * SS, 0), (x, rnd.uniform(140, 380) * SS)], fill=(70, 56, 48))
    d.rectangle([0, bh * 0.66, bw, bh], fill=(80, 64, 52))
    for k in range(6):  # string lights
        x = bw * (0.1 + k * 0.16)
        y = bh * 0.3 + math.sin(k) * 30 * SS
        glow = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(glow).ellipse([x - 90 * SS, y - 90 * SS, x + 90 * SS, y + 90 * SS], fill=120)
        glow = glow.filter(ImageFilter.GaussianBlur(30 * SS))
        img.paste((255, 200, 120), (0, 0), glow)
        d = ImageDraw.Draw(img)
        d.ellipse([x - 16 * SS, y - 16 * SS, x + 16 * SS, y + 16 * SS], fill=(255, 230, 160))
    # greenhouse grow lights
    d.rectangle([bw * 0.55, bh * 0.52, bw * 0.95, bh * 0.66], fill=(40, 120, 70))
    d.rectangle([bw * 0.55, bh * 0.48, bw * 0.95, bh * 0.5], fill=(220, 120, 255))
    return img


def earth(t: float, drift: float = 0.0) -> Image.Image:
    """Earth as a small planet; drift moves it right over time for the 'flying off' shot."""
    s = 420 * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    r = 170 * SS
    d.ellipse([c - r, c - r, c + r, c + r], fill=(40, 100, 200))
    rnd = random.Random(1)
    for k in range(7):
        a = rnd.uniform(0, math.tau)
        rr = rnd.uniform(0.2, 0.7) * r
        x, y = c + math.cos(a + t * 0.2) * rr, c + math.sin(a) * rr * 0.8
        if (x - c) ** 2 + (y - c) ** 2 < (r * 0.85) ** 2:
            d.ellipse([x - 50 * SS, y - 34 * SS, x + 50 * SS, y + 34 * SS], fill=(70, 150, 90))
    # night shade (no sun: whole planet dark-ish)
    shade = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(shade).ellipse([c - r, c - r, c + r, c + r], fill=(0, 0, 20, 150))
    img.alpha_composite(shade)
    return _down(img)


@lru_cache(maxsize=8)
def sun_disc(alpha: float) -> Image.Image:
    s = 700
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    if alpha <= 0:
        return img
    glow = Image.new("L", (s, s), 0)
    ImageDraw.Draw(glow).ellipse([60, 60, s - 60, s - 60], fill=int(200 * alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    layer = Image.new("RGBA", (s, s), (255, 220, 120, 0))
    layer.putalpha(glow)
    img.alpha_composite(layer)
    ImageDraw.Draw(img).ellipse([200, 200, s - 200, s - 200], fill=(255, 240, 170, int(255 * alpha)))
    return img


# ---------------------------------------------------------------- modern scenes (long-form)

def _glow(img, x, y, r, col, a=120):
    g = Image.new("L", img.size, 0)
    ImageDraw.Draw(g).ellipse([x - r, y - r, x + r, y + r], fill=a)
    g = g.filter(ImageFilter.GaussianBlur(r / 3))
    img.paste(col, (0, 0), g)


def _home(bw, bh, night: bool):
    u = min(bw, bh) / 1000
    wall = (64, 70, 108) if night else (238, 222, 196)
    img = _gradient((bw, bh), _lerp(wall, (0, 0, 0), 0.15), wall)
    d = ImageDraw.Draw(img)
    floor = bh * 0.62
    d.rectangle([0, floor, bw, bh], fill=(70, 52, 48) if night else (176, 128, 88))
    for k in range(0, int(bw), int(120 * u)):  # floorboards
        d.line([(k, floor), (k - 60 * u, bh)], fill=(60, 44, 40) if night else (156, 112, 78), width=int(3 * u))
    d.rectangle([0, floor - 14 * u, bw, floor], fill=(50, 40, 40) if night else (200, 180, 150))
    # window
    wx0, wy0, ww, wh = bw * 0.12, bh * 0.2, 300 * u, 330 * u
    d.rectangle([wx0 - 14 * u, wy0 - 14 * u, wx0 + ww + 14 * u, wy0 + wh + 14 * u], fill=(250, 246, 236) if not night else (40, 44, 70))
    sky = _gradient((int(ww), int(wh)), (14, 20, 50), (40, 50, 96)) if night else _gradient((int(ww), int(wh)), (120, 186, 240), (200, 230, 250))
    img.paste(sky, (int(wx0), int(wy0)))
    d = ImageDraw.Draw(img)
    if night:
        d.ellipse([wx0 + ww * 0.62, wy0 + wh * 0.12, wx0 + ww * 0.82, wy0 + wh * 0.12 + ww * 0.2], fill=(240, 236, 210))
        rnd = random.Random(2)
        for _ in range(30):
            x, y = wx0 + rnd.uniform(0, ww), wy0 + rnd.uniform(wh * 0.55, wh)
            d.rectangle([x, y, x + 8 * u, y + 10 * u], fill=(255, 214, 120))
    d.line([(wx0 + ww / 2, wy0), (wx0 + ww / 2, wy0 + wh)], fill=(250, 246, 236) if not night else (40, 44, 70), width=int(12 * u))
    d.line([(wx0, wy0 + wh / 2), (wx0 + ww, wy0 + wh / 2)], fill=(250, 246, 236) if not night else (40, 44, 70), width=int(12 * u))
    # frames on the wall
    for i, (fx_, col) in enumerate(((0.55, (230, 120, 90)), (0.68, (90, 160, 200)), (0.8, (240, 200, 90)))):
        x = bw * fx_
        d.rectangle([x, bh * 0.25 + i % 2 * 40 * u, x + 110 * u, bh * 0.25 + 140 * u + i % 2 * 40 * u], fill=(60, 44, 36))
        d.rectangle([x + 12 * u, bh * 0.25 + 12 * u + i % 2 * 40 * u, x + 98 * u, bh * 0.25 + 128 * u + i % 2 * 40 * u], fill=col)
    # couch
    cx0, cy0 = bw * 0.52, floor - 170 * u
    couch = (60, 110, 150) if not night else (40, 70, 100)
    d.rounded_rectangle([cx0, cy0, cx0 + 520 * u, cy0 + 150 * u], radius=int(40 * u), fill=couch)
    d.rounded_rectangle([cx0 - 30 * u, cy0 + 60 * u, cx0 + 550 * u, cy0 + 200 * u], radius=int(40 * u), fill=_lerp(couch, (255, 255, 255), 0.12))
    # floor lamp
    lx = bw * 0.94
    d.line([(lx, floor + 20 * u), (lx, floor - 360 * u)], fill=(40, 36, 40), width=int(8 * u))
    d.polygon([(lx - 70 * u, floor - 330 * u), (lx + 70 * u, floor - 330 * u), (lx + 45 * u, floor - 420 * u), (lx - 45 * u, floor - 420 * u)], fill=(250, 220, 160))
    if night:
        _glow(img, lx, floor - 300 * u, 360 * u, (255, 200, 120), 110)
    return img


def _clinic(bw, bh):
    u = min(bw, bh) / 1000
    img = _gradient((bw, bh), (200, 228, 222), (226, 242, 238))
    d = ImageDraw.Draw(img)
    floor = bh * 0.62
    d.rectangle([0, floor, bw, bh], fill=(196, 204, 212))
    for k in range(0, int(bw), int(140 * u)):
        d.line([(k, floor), (k, bh)], fill=(180, 188, 198), width=int(3 * u))
    for k in range(int(floor), int(bh), int(90 * u)):
        d.line([(0, k), (bw, k)], fill=(180, 188, 198), width=int(3 * u))
    # window with blinds
    wx0, wy0, ww, wh = bw * 0.08, bh * 0.18, 340 * u, 300 * u
    d.rectangle([wx0, wy0, wx0 + ww, wy0 + wh], fill=(170, 210, 240))
    for k in range(12):
        y = wy0 + k * wh / 12
        d.rectangle([wx0, y, wx0 + ww, y + wh / 24], fill=(236, 240, 244))
    # x-ray light box
    bx = bw * 0.58
    d.rectangle([bx, bh * 0.2, bx + 260 * u, bh * 0.2 + 300 * u], fill=(40, 46, 60))
    d.rectangle([bx + 14 * u, bh * 0.2 + 14 * u, bx + 246 * u, bh * 0.2 + 286 * u], fill=(150, 190, 220))
    for k in range(6):  # ribs
        y = bh * 0.2 + 70 * u + k * 30 * u
        d.arc([bx + 40 * u, y - 20 * u, bx + 220 * u, y + 40 * u], 200, 340, fill=(240, 248, 255), width=int(8 * u))
    d.line([(bx + 130 * u, bh * 0.2 + 50 * u), (bx + 130 * u, bh * 0.2 + 260 * u)], fill=(240, 248, 255), width=int(10 * u))
    # wall clock
    ccx, ccy, r = bw * 0.86, bh * 0.24, 70 * u
    d.ellipse([ccx - r, ccy - r, ccx + r, ccy + r], fill=(255, 255, 255), outline=(50, 56, 70), width=int(8 * u))
    d.line([(ccx, ccy), (ccx, ccy - r * 0.7)], fill=(50, 56, 70), width=int(6 * u))
    d.line([(ccx, ccy), (ccx + r * 0.5, ccy)], fill=(50, 56, 70), width=int(6 * u))
    # desk
    d.rectangle([bw * 0.6, floor - 120 * u, bw * 0.98, floor - 90 * u], fill=(140, 110, 84))
    d.rectangle([bw * 0.62, floor - 90 * u, bw * 0.64, floor + 40 * u], fill=(120, 94, 72))
    d.rectangle([bw * 0.94, floor - 90 * u, bw * 0.96, floor + 40 * u], fill=(120, 94, 72))
    return img


def _rooftop(bw, bh):
    u = min(bw, bh) / 1000
    img = _gradient((bw, bh), (44, 40, 96), (255, 170, 110))
    horizon = bh * 0.56
    _glow(img, bw * 0.5, horizon, 420 * u, (255, 220, 150), 170)
    d = ImageDraw.Draw(img)
    d.ellipse([bw * 0.5 - 120 * u, horizon - 120 * u, bw * 0.5 + 120 * u, horizon + 120 * u], fill=(255, 236, 180))
    _skyline(d, bw, horizon + 40 * u, (60, 44, 80), windows=(255, 200, 120), seed=9)
    d.rectangle([0, bh * 0.62, bw, bh], fill=(70, 66, 80))
    d.rectangle([0, bh * 0.62, bw, bh * 0.62 + 26 * u], fill=(110, 104, 118))
    for k in range(5):  # roof vents
        x = bw * (0.1 + k * 0.22)
        d.rectangle([x, bh * 0.66, x + 50 * u, bh * 0.66 + 70 * u], fill=(90, 86, 100))
    return img


def _street(bw, bh):
    u = min(bw, bh) / 1000
    img = _gradient((bw, bh), (8, 10, 26), (30, 30, 60))
    d = ImageDraw.Draw(img)
    rnd = random.Random(12)
    for _ in range(120):
        x, y = rnd.uniform(0, bw), rnd.uniform(0, bh * 0.3)
        d.ellipse([x - 2 * u, y - 2 * u, x + 2 * u, y + 2 * u], fill=(220, 226, 255))
    _skyline(d, bw, bh * 0.62, (24, 26, 46), windows=(255, 210, 120), seed=3)
    d.rectangle([0, bh * 0.62, bw, bh], fill=(36, 36, 44))
    d.rectangle([0, bh * 0.62, bw, bh * 0.66], fill=(70, 70, 80))
    for k in range(0, int(bw), int(220 * u)):
        d.rectangle([k, bh * 0.8, k + 110 * u, bh * 0.81], fill=(230, 210, 120))
    for x in (bw * 0.15, bw * 0.55, bw * 0.9):  # street lamps
        d.line([(x, bh * 0.64), (x, bh * 0.34)], fill=(20, 20, 26), width=int(10 * u))
        d.ellipse([x - 22 * u, bh * 0.34 - 22 * u, x + 22 * u, bh * 0.34 + 22 * u], fill=(255, 230, 170))
        _glow(img, x, bh * 0.36, 260 * u, (255, 200, 120), 90)
        d = ImageDraw.Draw(img)
    return img
