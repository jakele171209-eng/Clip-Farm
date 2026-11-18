"""Flat 2D art drawn in code: backgrounds, characters, labels and cards.

Everything is drawn at 2x and scaled down, which gives smooth edges without
an anti-aliasing library. All art here is original to this project.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
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
    "sailor": dict(coat=(120, 92, 70), hat=(70, 80, 100), skin=(236, 196, 160), hat_style="cap", hair=None),
    "sailor2": dict(coat=(90, 96, 112), hat=(150, 50, 50), skin=(222, 178, 140), hat_style="cap", hair=None),
    "guide": dict(coat=(176, 128, 84), hat=None, skin=(196, 140, 100), hat_style=None, hair=(40, 30, 26)),
    "woman": dict(coat=(160, 112, 76), hat=None, skin=(200, 146, 106), hat_style=None, hair=(36, 28, 24), long_hair=True),
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
    if who == "hero":  # zipper + collar
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
    for sx in (-1, 1):
        x = cx + sx * ex
        if blink or mood in ("happy", "smug"):
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
    if mood in ("worried", "sick", "cold", "awkward"):
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
    else:  # calm / flat
        d.line([(cx - 22 * SS, my + 6 * SS), (cx + 22 * SS, my + 6 * SS)], fill=ink, width=7 * SS)
    if mood == "awkward":  # sweat drop
        d.ellipse([cx + hr * 0.75, hy - 40 * SS, cx + hr * 0.75 + 26 * SS, hy - 4 * SS], fill=(150, 210, 250))
    if mood == "cold":  # breath puff
        d.ellipse([cx + 60 * SS, my - 10 * SS, cx + 110 * SS, my + 30 * SS], fill=(255, 255, 255, 170))
    out = _down(img)
    if scale != 1.0:
        out = out.resize((int(out.width * scale), int(out.height * scale)), Image.LANCZOS)
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
    for i, (txt, tag) in enumerate(rows[:shown]):
        y = 150 * SS + i * row_h
        d.rounded_rectangle([30 * SS, y, cw - 30 * SS, y + row_h - 18 * SS], radius=18 * SS, fill=(255, 255, 255))
        d.text((60 * SS, y + (row_h - 18 * SS) / 2), txt, font=font(42 * SS, "semi"), fill=(30, 30, 40), anchor="lm")
        good = tag.upper() in ("YES", "KNOWN", "OK")
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
