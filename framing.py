#!/usr/bin/env python3
"""Frame a retrieved picture into the standard over-the-shoulder corner.

Input: any image file (poster, logo, photo, screenshot). Output: a 1920×1080
transparent PNG with the picture sized to the corner box, rounded, hairlined,
shadowed, and credited — so in Descript it is one more overlay to drop and fade,
never something to resize by hand.

    python3 framing.py pictures/raw/pic-tarot.jpg "Rider–Waite deck, 1909 (public domain)" out/pic-tarot.png
"""
import math, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from style import W, H, PIP, MATTE, WARM, DIM, INT, INT_B
from overlays import font, new, shadowed, tracked


def _load(src, matte="trim", crop=None):
    """Open a picture and deal with the mount it was scanned on.

    `crop` is the one case where the SUBJECT is cut, and it is deliberate and declared in the
    cue rather than guessed here: (left, top, right, bottom) as fractions of the source. The
    reason is almost always that the painting is right but only part of it is on her beat — a
    wide canvas with the moment she describes in one corner, or a detail that would be a smudge
    at corner size. Written as fractions so the same cue survives a better scan of the same work.

    Museum and library scans of a single object almost always arrive on a flat white or flat
    black card, and a bright card over her shoulder reads as a graphic rather than as a thing.
    'trim' crops that dead margin away — a crop of the mount, never of the subject, so the
    constant-area rule then gives the OBJECT the standard weight instead of the object plus its
    border. 'knockout' goes further and makes the mount transparent, so a ragged object floats
    on her wall; it only makes sense when the mount is clearly separable from the subject, so it
    is opt-in per picture. 'keep' does nothing.
    """
    im = Image.open(src).convert("RGBA")
    if crop:
        l, t, r, b = crop
        im = im.crop((round(l * im.width), round(t * im.height),
                      round(r * im.width), round(b * im.height)))
    if matte == "paper":
        # A scan someone has cut out of its page, its paper made transparent (S2E9: Commons' Astaroth from the
        # Dictionnaire infernal). Over her shoulder it would be black lines floating on her wall; set back on a warm
        # paper tone it reads as what it is, a page of an old book. Then it is trimmed like any other picture.
        page = Image.new("RGBA", im.size, MATTE["paper"] + (255,))
        im = Image.alpha_composite(page, im)
        matte = "trim"
    if matte == "keep":
        return im
    tol = MATTE["tol"]
    px = im.convert("RGB")
    corners = [px.getpixel(p) for p in ((0, 0), (px.width - 1, 0), (0, px.height - 1), (px.width - 1, px.height - 1))]
    base = corners[0]
    if any(max(abs(a - b) for a, b in zip(c, base)) > tol for c in corners):
        # no uniform mount; leave it alone — unless knockout was asked for, in which case look for a
        # flat coloured surround instead (a 3D viewer's grey round a scanned slab, S2E7)
        return _knockout_surround(im) if matte == "knockout" else im
    if not (min(base) >= MATTE["light"] or max(base) <= MATTE["dark"]):
        # a mount is white or black, not a colour — but a declared knockout may still drop a flat
        # coloured surround, because someone has looked at the picture and said it is one
        return _knockout_surround(im) if matte == "knockout" else im

    def uniform(strip):
        return all(max(abs(a - b) for a, b in zip(p, base)) <= tol for p in strip)

    l, r, t, b = 0, px.width - 1, 0, px.height - 1
    lim_x, lim_y = int(px.width * MATTE["max_crop"]), int(px.height * MATTE["max_crop"])
    while l < lim_x and uniform([px.getpixel((l, y)) for y in range(t, b + 1, max(1, (b - t) // 200))]): l += 1
    while r > px.width - 1 - lim_x and uniform([px.getpixel((r, y)) for y in range(t, b + 1, max(1, (b - t) // 200))]): r -= 1
    while t < lim_y and uniform([px.getpixel((x, t)) for x in range(l, r + 1, max(1, (r - l) // 200))]): t += 1
    while b > px.height - 1 - lim_y and uniform([px.getpixel((x, b)) for x in range(l, r + 1, max(1, (r - l) // 200))]): b -= 1
    pad = MATTE["pad"]
    box = (max(0, l - pad), max(0, t - pad), min(px.width, r + 1 + pad), min(px.height, b + 1 + pad))
    if box[2] - box[0] < 8 or box[3] - box[1] < 8:
        return im
    im = im.crop(box)

    if matte == "knockout":
        im = _knockout(im, base, tol)
    return im


def _knockout(im, base, tol):
    """Make the mount transparent where it connects to the edge of the frame, and only there.

    Edge-connected, so a light patch INSIDE the subject — a blown-out highlight, a gap in a
    ragged papyrus that the object surrounds — stays opaque. Done as one flood fill on a
    one-bit mask rather than a walk in Python, which matters on a 4000-pixel scan.
    """
    rgb = im.convert("RGB")
    lo = tuple(max(0, c - tol) for c in base)
    hi = tuple(min(255, c + tol) for c in base)
    # a band-wise range check, which Pillow does in C
    bands = rgb.split()
    mount = None
    for b, l, h in zip(bands, lo, hi):
        m = b.point(lambda v, l=l, h=h: 255 if l <= v <= h else 0, mode="L")
        mount = m if mount is None else ImageChops.darker(mount, m)

    # pad by one pixel of mount so a single flood from the corner reaches every edge
    w, h_ = mount.size
    pad = Image.new("L", (w + 2, h_ + 2), 255)
    pad.paste(mount, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128, thresh=0)       # 255 -> 128 wherever it is connected
    outside = pad.crop((1, 1, w + 1, h_ + 1)).point(lambda v: 0 if v == 128 else 255, mode="L")

    alpha = ImageChops.darker(im.split()[3], outside)
    im = im.copy(); im.putalpha(alpha)
    return im


def _knockout_surround(im):
    """Drop a flat COLOURED surround — the grey of a 3D viewer behind a scanned slab, a museum's
    backdrop — when knockout has been declared on the cue. The surround colour is the median of
    the outer ring, it must cover most of that ring (MATTE['surround_share']) or nothing happens,
    and only pixels connected to the edge go, exactly as with a white or black mount. The edge is
    softened by a fraction of a pixel and the result cropped to what is left. The tolerance is
    deliberately tight: on S2E7's relief, 18 dropped the viewer's grey cleanly and 28 ate into
    the stone, which is only a few shades lighter."""
    rgb = im.convert("RGB"); w, h = rgb.size
    ring = ([rgb.getpixel((x, 0)) for x in range(0, w, 2)] + [rgb.getpixel((x, h - 1)) for x in range(0, w, 2)]
            + [rgb.getpixel((0, y)) for y in range(0, h, 2)] + [rgb.getpixel((w - 1, y)) for y in range(0, h, 2)])
    base = tuple(sorted(c[i] for c in ring)[len(ring) // 2] for i in range(3))
    tol = MATTE["surround_tol"]
    share = sum(1 for c in ring if max(abs(a - b) for a, b in zip(c, base)) <= tol) / len(ring)
    if share < MATTE["surround_share"]:
        return im                                        # no flat surround to drop
    out = _knockout(im, base, tol)
    a = out.split()[3]
    a = ImageChops.darker(a, a.filter(ImageFilter.GaussianBlur(0.7)).point(lambda v: min(255, v * 2)))
    out.putalpha(a)
    box = a.getbbox()
    return out.crop(box) if box else out


def frame_picture(src, credit=None, side=None, matte="trim", crop=None):
    """Constant area, not constant aspect: every picture carries the same visual weight and the
    credit lands in the same place, whatever shape the source is. Nothing is ever cropped."""
    P = PIP; side = side or P["side"]
    im = _load(src, matte, crop)
    ar = im.width / im.height
    h = math.sqrt(P["area"] / ar); w = P["area"] / h
    k = min(P["max_w"] / w, P["max_h"] / h, 1.0)          # clamp the extremes only
    im = im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
    w, h = im.size
    x = (W - P["margin"] - w) if side == "right" else P["margin"]
    y = P["top"] + P["band_h"] - h                        # bottom edge on the shelf, whatever the shape
    r = P["radius"]

    canvas = new()
    cut = im.split()[3].getextrema()[0] == 0            # knocked out: the object has its own shape

    # shadow — the picture is a physical object floating in front of the wall. When the mount has
    # been dropped out there is no card to cast one, so the shadow is taken from the object itself.
    sh = new()
    if cut:
        sh.paste((0, 0, 0, 165), (x, y + 12), im.split()[3])
    else:
        ImageDraw.Draw(sh).rounded_rectangle([x, y + 12, x + w, y + h + 12], radius=r, fill=(0, 0, 0, 165))
    sh = sh.filter(ImageFilter.GaussianBlur(24))
    canvas = Image.alpha_composite(canvas, sh)

    # the picture — rounded to the card, or left in its own shape if there is no card
    pic = new()
    if cut:
        pic.paste(im, (x, y), im)
    else:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
        pic.paste(im, (x, y), mask)
    canvas = Image.alpha_composite(canvas, pic)

    # hairline — the edge of the card. A cut-out object has no card, so it gets none.
    if not cut:
        line = new()
        ImageDraw.Draw(line).rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=r,
                                               outline=WARM + (P["border_alpha"],), width=1)
        canvas = Image.alpha_composite(canvas, line)

    # credit — set to the picture's own measure, tight under the shelf, with the same soft
    # shadow as every other label. Justified on the word spaces; wraps if it has to.
    if credit:
        ty = P["top"] + P["band_h"] + P["credit_gap"]     # tight under the shelf, and never moves
        f, lines = _justify(ImageDraw.Draw(canvas), credit, w, P)
        lead = round(f.size * P["credit_leading"])

        shd = new(); _draw_justified(ImageDraw.Draw(shd), x, ty + 2, lines, f, (0, 0, 0, 170), lead)
        canvas = Image.alpha_composite(canvas, shd.filter(ImageFilter.GaussianBlur(6)))
        txt = new(); _draw_justified(ImageDraw.Draw(txt), x, ty, lines, f, DIM, lead)
        canvas = Image.alpha_composite(canvas, txt)
    return canvas


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, credit = sys.argv[1], sys.argv[2] or None
    out = sys.argv[3] if len(sys.argv) > 3 else "pic.png"
    frame_picture(src, credit).save(out, optimize=True)   # photos are not quantized
    print("wrote", out)


# ───────── full frame ─────────
def _fit_line(d, words, fnt, target, P):
    """Gap needed to justify these words to `target`, or None if it is outside the limits."""
    if not words:
        return None
    span = sum(d.textlength(w, font=fnt) for w in words)
    gaps = len(words) - 1
    sp = d.textlength(" ", font=fnt) or fnt.size * 0.28
    if gaps == 0:
        return sp if span <= target else None
    g = (target - span) / gaps
    return g if sp * P["credit_space_min"] <= g <= sp * P["credit_space_max"] else None


def _justify(d, text, target, P):
    """Set `text` to the picture's own measure and return (font, [(words, gap), ...]).

    A caption belongs to its picture, so it is set to the picture's width rather than sitting
    near it at whatever length it happens to be. Two rules do the work. It is justified on the
    WORD SPACES and never on the letterforms — spacing out letters is a display treatment and
    these are sentence case. And it is set at the largest size in the allowed range that lets it
    fill that measure on one line, so most captions are a single line flush to both edges of the
    picture. Only a caption too long for one line even at the smallest size wraps; then it goes
    back to full size, the break is chosen to leave the last line as long as possible rather than
    a runt, and that last line is set flush left and NOT justified, the way the last line of any
    justified paragraph is.
    """
    words = text.split()
    if not words:
        return font(INT, P["credit_size"]), []

    # Pick the size whose word spaces come out CLOSEST to the font's own — the most naturally
    # set line, not merely the biggest one that squeezes in. A caption a little short for the
    # measure wants slightly larger type, not wider gaps; one a little long wants the reverse.
    best = None
    for size in range(P["credit_size_max"], P["credit_size_min"] - 1, -1):
        f = font(INT, size)
        g = _fit_line(d, words, f, target, P)
        if g is None:
            continue
        sp = d.textlength(" ", font=f) or f.size * 0.28
        dev = abs(g - sp) / sp
        if best is None or dev < best[0] - 1e-9:
            best = (dev, f, g)
    if best:
        return best[1], [(words, best[2])]

    # Too SHORT to reach the measure even at the largest size — a four-word caption under a wide
    # picture. Stretching it to fit would leave gaps you could park a bus in, so it is set at the
    # largest size, spaced normally, and left short. episode.py warns, because the real fix is a
    # caption written closer to the width of the picture it sits under.
    f = font(INT, P["credit_size_max"])
    natural = sum(d.textlength(w, font=f) for w in words) + (d.textlength(" ", font=f) or f.size * 0.28) * (len(words) - 1)
    if natural <= target:
        return f, [(words, d.textlength(" ", font=f) or f.size * 0.28)]

    f = font(INT, P["credit_size"])
    sp = d.textlength(" ", font=f) or f.size * 0.28
    import itertools
    for n in range(2, P["credit_lines_max"] + 1):
        best = None
        for cuts in itertools.combinations(range(1, len(words)), n - 1):
            bounds = [0] + list(cuts) + [len(words)]
            lines, ok = [], True
            for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
                chunk = words[lo:hi]
                if not chunk:
                    ok = False; break
                if i == n - 1:                                    # last line: flush left, never stretched
                    span = sum(d.textlength(w, font=f) for w in chunk) + sp * (len(chunk) - 1)
                    if span > target:
                        ok = False; break
                    lines.append((chunk, sp, target - span))      # carry its shortfall as the cost
                else:
                    g = _fit_line(d, chunk, f, target, P)
                    if g is None:
                        ok = False; break
                    lines.append((chunk, g, 0.0))
            if not ok:
                continue
            cost = lines[-1][2]                                   # how much of the last line is empty
            if best is None or cost < best[0]:
                best = (cost, [(c, g) for c, g, _ in lines])
        if best:
            return f, best[1]

    # Nothing fits the limits: greedy fill at full size, gaps clamped, last line flush left.
    lines, cur = [], []
    for w in words:
        trial = cur + [w]
        span = sum(d.textlength(t, font=f) for t in trial) + sp * (len(trial) - 1)
        if cur and span > target:
            lines.append(cur); cur = [w]
        else:
            cur = trial
    if cur:
        lines.append(cur)
    out = []
    for i, ln in enumerate(lines):
        if i == len(lines) - 1 or len(ln) == 1:
            out.append((ln, sp)); continue
        g = _fit_line(d, ln, f, target, P)
        if g is None:
            span = sum(d.textlength(t, font=f) for t in ln)
            g = min(sp * P["credit_space_max"], max(sp * P["credit_space_min"],
                                                    (target - span) / (len(ln) - 1)))
        out.append((ln, g))
    return f, out


def _draw_justified(d, x, y, lines, fnt, fill, leading):
    for i, (words, gap) in enumerate(lines):
        cx = x
        for w in words:
            d.text((cx, y + i * leading), w, font=fnt, fill=fill)
            cx += d.textlength(w, font=fnt) + gap


def _arrow(d, tip, tail, col, width, head, force=None):
    """A tapered shaft with a solid head, pointing at tip from tail."""
    import math as _m
    tx, ty = tip; ax, ay = tail
    dx, dy = tx - ax, ty - ay
    L = _m.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    px, py = -uy, ux                                   # perpendicular
    bx, by = tx - ux * head, ty - uy * head            # base of the head
    c = force or col
    d.polygon([(tx, ty), (bx + px * head * 0.42, by + py * head * 0.42),
               (bx - px * head * 0.42, by - py * head * 0.42)], fill=c)
    d.polygon([(ax + px * width * 0.30, ay + py * width * 0.30),
               (bx + px * width * 0.62, by + py * width * 0.62),
               (bx - px * width * 0.62, by - py * width * 0.62),
               (ax - px * width * 0.30, ay - py * width * 0.30)], fill=c)


def frame_full(src, credit=None, arrow=None, grid=False, matte="trim", crop=None, credit_below=True):
    """The picture at full frame, on a dark ground. `arrow` = dict(at=(x,y) 0-1 in the
    picture, from_deg=direction the tail lies in, length=fraction of frame, label=str)."""
    import math as _m
    from style import FULL
    F = FULL
    im = _load(src, matte, crop)
    # The caption gets its own line under the picture (S2E7): a picture as wide as the frame used to run down under
    # it, and light type on a light engraving could not be read. So the picture fits the space ABOVE the caption,
    # and the caption sits under the picture's own right edge rather than at the corner of the frame.
    # A full-frame MAP keeps its caption in the frame's corner (credit_below=False, from maps.py): it sits on the
    # map's own dark sea, and the maps already shipped that way.
    cap = (F["credit_size"] + F["credit_gap"]) if (credit and credit_below) else 0
    avail_w, avail_h = W - 2 * F["margin"], H - 2 * F["margin"] - cap
    k = min(avail_w / im.width, avail_h / im.height)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    ox, oy = (W - im.width) // 2, F["margin"] + (avail_h - im.height) // 2

    canvas = Image.new("RGBA", (W, H), F["ground"] + (255,))
    canvas.alpha_composite(im, (ox, oy))

    if grid:                                            # for reading off an arrow target
        g = new(); dg = ImageDraw.Draw(g); f = font(INT, 20)
        for i in range(1, 10):
            x = ox + im.width * i / 10; y = oy + im.height * i / 10
            dg.line([(x, oy), (x, oy + im.height)], fill=(255, 255, 255, 70), width=1)
            dg.line([(ox, y), (ox + im.width, y)], fill=(255, 255, 255, 70), width=1)
            dg.text((x + 4, oy + 4), f".{i}", font=f, fill=(255, 255, 255, 190))
            dg.text((ox + 4, y + 4), f".{i}", font=f, fill=(255, 255, 255, 190))
        canvas = Image.alpha_composite(canvas, g)

    if arrow:
        A = F["arrow"]
        tx = ox + im.width * arrow["at"][0]
        ty = oy + im.height * arrow["at"][1]
        ang = _m.radians(arrow.get("from_deg", 225))
        ln = arrow.get("length", A["length"]) * H
        gap = A["gap"] * H
        tipx, tipy = tx + _m.cos(ang) * gap, ty - _m.sin(ang) * gap
        ax, ay = tx + _m.cos(ang) * (gap + ln), ty - _m.sin(ang) * (gap + ln)

        def draw(d, force):
            _arrow(d, (tipx, tipy), (ax, ay), A["colour"], A["width"], A["head"], force)
            if arrow.get("label"):
                f = font(INT_B, A["label_size"])
                lx = ax + _m.cos(ang) * 26; ly = ay - _m.sin(ang) * 26
                tracked(d, (lx, ly - A["label_size"] / 2), arrow["label"].upper(), f,
                        force or A["colour"], A["label_track"],
                        center=(90 < arrow.get("from_deg", 225) % 360 < 270) is False)
        canvas = shadowed(canvas, draw, blur=16, alpha=170, off=(0, 3))

    if credit:
        f = font(INT, F["credit_size"])
        at = ((ox + im.width, oy + im.height + F["credit_gap"]) if credit_below
              else (W - F["margin"], H - F["margin"] - F["credit_size"]))
        def draw(d, force):
            d.text(at, credit, font=f, fill=force or DIM, anchor="ra")
        canvas = shadowed(canvas, draw, blur=8, alpha=180)
    return canvas


# ───────── across the bottom ─────────
def frame_strip(src, credit=None, matte="trim", crop=None):
    """A very wide picture laid across the bottom of the frame, over her (added for S2E7).

    The width is the frame less two margins; the height follows the shape, capped at STRIP['max_h'],
    above which the picture is scaled down and centred instead. It casts the same shadow as a picture
    in the corner — from its card, or from its own outline when the surround has been knocked out —
    and its caption sits under it, flush with its left edge, like a museum label."""
    from style import STRIP
    S = STRIP
    im = _load(src, matte, crop)
    cap = (S["credit_gap"] + S["credit_size"]) if credit else 0
    k = (W - 2 * S["margin"]) / im.width
    if im.height * k > S["max_h"]:
        k = S["max_h"] / im.height
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    w, h = im.size
    x = (W - w) // 2
    y = H - S["bottom"] - cap - h
    r = S["radius"]
    cut = im.split()[3].getextrema()[0] == 0

    canvas = new()
    sh = new()
    if cut:
        sh.paste((0, 0, 0, S["shadow_alpha"]), (x, y + S["shadow_off"]), im.split()[3])
    else:
        ImageDraw.Draw(sh).rounded_rectangle([x, y + S["shadow_off"], x + w, y + h + S["shadow_off"]], radius=r,
                                             fill=(0, 0, 0, S["shadow_alpha"]))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(S["shadow_blur"])))

    pic = new()
    if cut:
        pic.paste(im, (x, y), im)
    else:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
        pic.paste(im, (x, y), mask)
    canvas = Image.alpha_composite(canvas, pic)
    if not cut:
        line = new()
        ImageDraw.Draw(line).rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=r,
                                               outline=WARM + (S["border_alpha"],), width=1)
        canvas = Image.alpha_composite(canvas, line)

    if credit:
        f = font(INT, S["credit_size"])
        ty = y + h + S["credit_gap"]
        shd = new(); ImageDraw.Draw(shd).text((x, ty + 2), credit, font=f, fill=(0, 0, 0, 170))
        canvas = Image.alpha_composite(canvas, shd.filter(ImageFilter.GaussianBlur(6)))
        txt = new(); ImageDraw.Draw(txt).text((x, ty), credit, font=f, fill=DIM)
        canvas = Image.alpha_composite(canvas, txt)
    return canvas
