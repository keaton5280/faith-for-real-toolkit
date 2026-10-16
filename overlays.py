#!/usr/bin/env python3
"""Overlay renderer — text ON the footage, never cards. Every builder returns a
1920×1080 RGBA image; build(cue) dispatches on the cue's kind."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from style import (W, H, FONT_DIR, GAR, GAR_R, GAR_B, GAR_I, INT, INT_B,
                   WARM, GOLD, DIM, SCRIM)

HERE = os.path.dirname(os.path.abspath(__file__))
PUNCT = ",.;:—“”’\""

# ───────── primitives ─────────
_FC = {}
def font(n, s):
    k = (n, int(s))
    if k not in _FC:
        _FC[k] = ImageFont.truetype(os.path.join(HERE, FONT_DIR, n), int(s))
    return _FC[k]

def wrap(d, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=fnt) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = wd
    if cur: lines.append(cur)
    return lines

def fit(d, text, name, maxw, maxlines, hi, lo=34):
    for s in range(hi, lo - 1, -2):
        f = font(name, s)
        if len(wrap(d, text, f, maxw)) <= maxlines: return f, wrap(d, text, f, maxw)
    f = font(name, lo); return f, wrap(d, text, f, maxw)

def tracked(d, xy, text, fnt, fill, track=0, center=False):
    ws = [d.textlength(c, font=fnt) for c in text]
    total = sum(ws) + track * (len(text) - 1)
    x, y = xy
    if center: x -= total / 2
    for c, w in zip(text, ws):
        d.text((x, y), c, font=fnt, fill=fill); x += w + track
    return total

def new(): return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def scrim_bottom(img, top=0.42, peak=170):
    """Soft dark gradient rising from the bottom edge."""
    a = np.zeros((H, W), dtype=float)
    ys = np.arange(H)
    t = np.clip((ys - H * top) / (H * (1 - top)), 0, 1)
    t = t * t * (3 - 2 * t)
    a[:, :] = (t * peak)[:, None]
    lay = Image.new("RGBA", (W, H), SCRIM + (0,))
    lay.putalpha(Image.fromarray(a.astype("uint8"), "L"))
    return Image.alpha_composite(lay, img)

def scrim_full(img, peak=105):
    lay = Image.new("RGBA", (W, H), SCRIM + (peak,))
    return Image.alpha_composite(lay, img)

def shadowed(base, draw_fn, blur=14, alpha=150, off=(0, 3)):
    """Render text twice — a soft dark pass under a clean pass."""
    sh = new(); d = ImageDraw.Draw(sh)
    draw_fn(d, (0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh = Image.fromarray(np.roll(np.asarray(sh), off[1], axis=0))
    out = Image.alpha_composite(base, sh)
    tx = new(); d2 = ImageDraw.Draw(tx)
    draw_fn(d2, None)
    return Image.alpha_composite(out, tx)

def save_quantized(im, path, colors=48):
    """Alpha-preserving palette PNG — 2–4 MB instead of 70."""
    a = im.split()[3]
    q = im.convert("RGB").quantize(colors=colors, method=Image.MEDIANCUT).convert("RGBA")
    q.putalpha(a)
    q.save(path, optimize=True)

# ───────── builders ─────────
# (share of the frame width, most lines, largest px, smallest px) — the fitter steps down from the largest size until
# the verse fits in that many lines, so a long verse comes out small. verse_size() reports where it landed.
VERSE_FIT = {"dim": (.70, 4, 100, 48), "band": (.74, 3, 88, 46)}


def verse_size(text, mode="band"):
    """(px the verse is set at, lines it takes, lines allowed) — render.py warns on a size a phone can't read."""
    share, most, hi, lo = VERSE_FIT["dim" if mode == "dim" else "band"]
    f, lines = fit(ImageDraw.Draw(new()), text, GAR, int(W * share), most, hi, lo)
    return f.size, len(lines), most


def scripture(text, ref, mode="band", hl=None):
    if mode == "dim":
        img = scrim_full(new(), peak=118); d0 = ImageDraw.Draw(img)
        share, most, hi, lo = VERSE_FIT["dim"]
        bw = int(W * share); f, lines = fit(d0, text, GAR, bw, most, hi, lo)
        lh = int(f.size * 1.32); blk = lh * len(lines) + 60; y0 = (H - blk) / 2 + 20
        cx = W / 2
    else:
        img = scrim_bottom(new(), top=.40, peak=175); d0 = ImageDraw.Draw(img)
        share, most, hi, lo = VERSE_FIT["band"]
        bw = int(W * share); f, lines = fit(d0, text, GAR, bw, most, hi, lo)
        lh = int(f.size * 1.30); blk = lh * len(lines) + 46; y0 = H - 104 - blk
        cx = W / 2
    def draw(d, force):
        y = y0
        for ln in lines:
            if hl and any(w.strip(PUNCT) == hl for w in ln.split()):
                x = cx - d.textlength(ln, font=f) / 2
                for word in ln.split():
                    col = force or (GOLD if word.strip(PUNCT) == hl else WARM)
                    d.text((x, y), word, font=f, fill=col)
                    x += d.textlength(word + " ", font=f)
            else:
                d.text((cx, y), ln, font=f, fill=force or WARM, anchor="ma")
            y += lh
        if mode == "dim":
            d.line([(cx - 42, y + 22), (cx + 42, y + 22)], fill=force or GOLD, width=2)
            tracked(d, (cx, y + 40), ref.upper(), font(INT_B, 24), force or GOLD, 5.5, True)
        else:
            tracked(d, (cx, y + 18), ref.upper(), font(INT_B, 24), force or GOLD, 5.5, True)
    return shadowed(img, draw, blur=16 if mode == "dim" else 14, alpha=140 if mode == "dim" else 150)

def quote(text, who, src=None):
    img = scrim_full(new(), peak=125); d0 = ImageDraw.Draw(img)
    bw = int(W * .68); f, lines = fit(d0, "“" + text + "”", GAR, bw, 3, 104, 52)
    lh = int(f.size * 1.30); blk = lh * len(lines) + 54 + (44 if src else 0); y0 = (H - blk) / 2 + 26
    def draw(d, force):
        y = y0
        for ln in lines:
            d.text((W / 2, y), ln, font=f, fill=force or WARM, anchor="ma"); y += lh
        y += 22
        tracked(d, (W / 2, y), who.upper(), font(INT_B, 25), force or GOLD, 5.5, True)
        if src:
            d.text((W / 2, y + 40), src, font=font(GAR_I, 34), fill=force or DIM, anchor="ma")
    return shadowed(img, draw, blur=16, alpha=140)

def names(lst, mode="band"):
    if mode == "dim":
        img = scrim_full(new(), peak=125); d0 = ImageDraw.Draw(img)
        f = font(GAR, 92); lh = int(92 * 1.55); blk = lh * len(lst); y0 = (H - blk) / 2 + 24
        def draw(d, force):
            y = y0
            for n in lst:
                d.text((W / 2, y), n, font=f, fill=force or WARM, anchor="ma"); y += lh
        return shadowed(img, draw, blur=16, alpha=140)
    img = scrim_bottom(new(), top=.44, peak=180); d0 = ImageDraw.Draw(img)
    f = font(GAR, 76); lh = int(76 * 1.42); blk = lh * len(lst); y0 = H - 130 - blk
    def draw(d, force):
        y = y0
        for n in lst:
            d.text((W / 2, y), n, font=f, fill=force or WARM, anchor="ma"); y += lh
    return shadowed(img, draw)

def figures(rows, src):
    img = scrim_bottom(new(), top=.30, peak=190); d0 = ImageDraw.Draw(img)
    fh = font(GAR_B, 108); fl = font(GAR_R, 36)
    hb = d0.textbbox((0, 0), "2,600+", font=fh, anchor="la")
    hadv = (hb[3] - hb[1]) + 10; ladv = int(36 * 1.5)
    colw = W * .26; xs = [W / 2 - colw, W / 2, W / 2 + colw]
    top = H - 118 - 40 - (hadv + ladv)
    def draw(d, force):
        for (num, lab), x in zip(rows, xs):
            d.text((x, top - hb[1]), num, font=fh, fill=force or GOLD, anchor="ma")
            d.text((x, top + hadv), lab, font=fl, fill=force or WARM, anchor="ma")
        tracked(d, (W / 2, H - 108), src.upper(), font(INT, 24), force or DIM, 4.5, True)
    return shadowed(img, draw)

def timeline(rows, between):
    img = scrim_bottom(new(), top=.36, peak=185); d0 = ImageDraw.Draw(img)
    fd = font(INT_B, 26); fb = font(GAR_R, 52)
    L = int(W * .10); bw = int(W * .80)
    wrapped = [wrap(d0, t, fb, bw) for _, t in rows]
    lh = int(52 * 1.34); rowh = [44 + lh * len(w) for w in wrapped]
    gap = 62; blk = sum(rowh) + gap; y0 = H - 120 - blk
    def draw(d, force):
        y = y0
        for i, ((date, _), lines) in enumerate(zip(rows, wrapped)):
            tracked(d, (L, y), date.upper(), fd, force or GOLD, 4.5); y += 44
            for ln in lines:
                d.text((L, y), ln, font=fb, fill=force or WARM); y += lh
            if i < len(rows) - 1:
                d.text((L + 2, y + 14), "↓  " + between, font=font(INT_B, 25), fill=force or GOLD)
                y += gap
    return shadowed(img, draw)

def kinetic(text):
    img = scrim_bottom(new(), top=.44, peak=175); d0 = ImageDraw.Draw(img)
    f = font(GAR, 96)
    while d0.textlength(text, font=f) > W * .84 and f.size > 60: f = font(GAR, f.size - 2)
    y0 = H - 118 - int(f.size * 1.1)
    def draw(d, force):
        d.text((W / 2, y0), text, font=f, fill=force or WARM, anchor="ma")
    return shadowed(img, draw)

def stat(hero, sub, sub2, src):
    img = scrim_bottom(new(), top=0.34, peak=185)
    d0 = ImageDraw.Draw(img)
    fh = font(GAR_B, 196)
    fs, subl = fit(d0, sub, GAR_R, int(W * 0.62), 2, 50, 30)
    fn = font(INT, 26)
    hb = d0.textbbox((0, 0), hero, font=fh, anchor="la")
    ink_top, ink_bot = hb[1], hb[3]
    hadv = (ink_bot - ink_top) + 38
    blk = hadv + int(fs.size * 1.32) * len(subl) + (44 if sub2 else 0) + 34
    y0 = H - 118 - blk
    def draw(d, force):
        y = y0
        d.text((W / 2, y - ink_top), hero, font=fh, fill=force or GOLD, anchor="ma"); y += hadv
        for ln in subl:
            d.text((W / 2, y), ln, font=fs, fill=force or WARM, anchor="ma"); y += int(fs.size * 1.32)
        if sub2:
            d.text((W / 2, y + 4), sub2, font=font(GAR_R, 38), fill=force or DIM, anchor="ma"); y += 40
        tracked(d, (W / 2, y + 16), src.upper(), fn, force or DIM, 4.5, True)
    return shadowed(img, draw)

def name(nm, role):
    img = scrim_bottom(new(), top=0.56, peak=175)
    d0 = ImageDraw.Draw(img)
    L = int(W * 0.10)
    fn = font(GAR_B, 82)
    fr, rl = fit(d0, role, GAR_R, int(W * 0.56), 2, 42, 26)
    nb = d0.textbbox((0, 0), nm, font=fn, anchor="la")
    nadv = (nb[3] - nb[1]) + 24
    blk = nadv + 26 + int(fr.size * 1.34) * len(rl)
    y0 = H - 128 - blk
    def draw(d, force):
        y = y0
        d.text((L, y - nb[1]), nm, font=fn, fill=force or WARM); y += nadv
        d.line([(L, y), (L + 62, y)], fill=force or GOLD, width=2); y += 26
        for ln in rl:
            d.text((L, y), ln, font=fr, fill=force or DIM); y += int(fr.size * 1.34)
    return shadowed(img, draw)

# ───────── dispatch ─────────
def build(cue):
    """Return one image for a single-frame overlay cue, or a list for kinetic."""
    k = cue["kind"]; m = cue.get("mode", "band")
    if k == "scripture": return scripture(cue["text"], cue["ref"], m, cue.get("hl"))
    if k == "quote":     return quote(cue["text"], cue["who"], cue.get("src"))
    if k == "names":     return names(list(cue["names"]), m)
    if k == "name":      return name(cue["name"], cue["role"])
    if k == "stat":      return stat(cue["hero"], cue["sub"], cue.get("sub2"), cue["src"])
    if k == "figures":   return figures([tuple(r) for r in cue["rows"]], cue["src"])
    if k == "timeline":  return timeline([tuple(r) for r in cue["rows"]], cue["between"])
    if k == "kinetic":   return [kinetic(s) for s in cue["steps"]]
    raise ValueError(f"{cue['id']}: no overlay builder for kind {k!r}")
