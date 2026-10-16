#!/usr/bin/env python3
"""Map cues — a coastline, the cities she names, and a dotted line that travels between them.

A map cue renders two ways from the same drawing, because the two are good at different things:

  STEPS   one PNG per leg, cumulative, exactly like kinetic text. The line reaches each city on
          its own scene, so it advances WITH HER WORDS rather than on a fixed clock. Best when she
          names three or four places in a sentence.
  MOTION  one silent .mov with a real alpha channel: the dot travels and the dots lay down behind
          it continuously. Best over a longer passage, where the words and the map are not in step.
          QuickTime Animation (qtrle), because Descript imported a VP9 WebM as a black rectangle —
          it is lossless, it is what editors have accepted for transparent overlays for thirty
          years, and on a frame that is mostly transparent it costs under 2 MB for six seconds.

Both are framed by the same code the pictures use, so a map lands in the same corner over her
shoulder, on the same shelf, with the same caption — or full frame, on the dark ground, for a
journey that needs the whole width.

Geography is Natural Earth 10m land, fetched and clipped once by setup_geo.py.
"""
import json, math, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFilter
from style import W, H, PIP, FULL, MAP, WARM, GOLD, DIM, INT, INT_B
from overlays import font, new
from framing import frame_picture, frame_full

HERE = os.path.dirname(os.path.abspath(__file__))
_LAND = None


def land():
    global _LAND
    if _LAND is None:
        p = os.path.join(HERE, "geo", "med.json")
        if not os.path.exists(p):
            raise SystemExit("no geo/med.json — run `python3 setup_geo.py` first")
        _LAND = json.load(open(p))["rings"]
    return _LAND


# ── the drawing surface ────────────────────────────────────────────────
def tile_size(mode, aspect):
    """Pick the tile so the framing code never has to resample it — labels stay crisp."""
    if mode == "full":
        w = W - 2 * FULL["margin"]; h = H - 2 * FULL["margin"]
        return (w, round(w / aspect)) if w / aspect <= h else (round(h * aspect), h)
    h = math.sqrt(PIP["area"] / aspect); w = PIP["area"] / h
    k = min(PIP["max_w"] / w, PIP["max_h"] / h, 1.0)
    return max(1, round(w * k)), max(1, round(h * k))


class Frame:
    """Equirectangular with the longitudes squeezed by cos(lat) — true enough at this size."""

    def __init__(self, pts, size, pad):
        lons = [p[1] for p in pts]; lats = [p[2] for p in pts]
        lat0 = (min(lats) + max(lats)) / 2
        self.k = math.cos(math.radians(lat0))
        x0, x1 = min(lons) * self.k, max(lons) * self.k
        y0, y1 = -max(lats), -min(lats)
        sx, sy = max(x1 - x0, 0.4), max(y1 - y0, 0.4)
        x0 -= sx * pad; x1 += sx * pad; y0 -= sy * pad; y1 += sy * pad
        w, h = size
        s = min(w / (x1 - x0), h / (y1 - y0))
        self.s = s
        self.ox = (w - (x1 - x0) * s) / 2 - x0 * s
        self.oy = (h - (y1 - y0) * s) / 2 - y0 * s

    def __call__(self, lon, lat):
        return lon * self.k * self.s + self.ox, -lat * self.s + self.oy


def base_tile(fr, size, scale):
    """Sea, land and coastline. Drawn once per cue and reused for every frame."""
    M = MAP
    im = Image.new("RGBA", size, M["sea"] + (255,))
    d = ImageDraw.Draw(im)
    w, h = size
    for ring in land():
        pts = [fr(lo, la) for lo, la in ring]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if max(xs) < -20 or min(xs) > w + 20 or max(ys) < -20 or min(ys) > h + 20:
            continue
        if len(pts) >= 3:
            d.polygon(pts, fill=M["land"] + (255,))
    for ring in land():                      # coast after every fill, so no island is overpainted
        pts = [fr(lo, la) for lo, la in ring]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if max(xs) < -20 or min(xs) > w + 20 or max(ys) < -20 or min(ys) > h + 20:
            continue
        d.line(pts + [pts[0]], fill=M["coast"] + (255,), width=max(1, round(scale)), joint="curve")
    return im


# ── the route ──────────────────────────────────────────────────────────
def path_points(fr, places, bow):
    """Screen points for the route, each leg bowed a little so a sea crossing reads as a voyage."""
    legs = []
    for (a, b) in zip(places, places[1:]):
        p0 = fr(a[1], a[2]); p1 = fr(b[1], b[2])
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy) or 1
        cx, cy = mx - dy / L * L * bow, my + dx / L * L * bow      # control point, bowed left of travel
        pts = [(( 1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * cx + t * t * p1[0],
                (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * cy + t * t * p1[1])
               for t in [i / 48 for i in range(49)]]
        legs.append(pts)
    return legs


def seg_lengths(pts):
    return [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]


def walk(legs, dist):
    """Everything up to `dist` along the concatenated legs, plus the point reached."""
    out, remaining, head = [], dist, None
    for pts in legs:
        seg = seg_lengths(pts); total = sum(seg)
        if remaining >= total:
            out.append(pts); remaining -= total; head = pts[-1]; continue
        run, acc = [pts[0]], 0.0
        for (a, b), L in zip(zip(pts, pts[1:]), seg):
            if acc + L <= remaining:
                run.append(b); acc += L
            else:
                t = (remaining - acc) / L if L else 0
                head = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                run.append(head); break
        out.append(run); remaining = 0; break
    if head is None and out:
        head = out[-1][-1]
    return out, head


def dotted(d, runs, scale):
    """Lay the line down as dots, evenly spaced along it, whatever shape the legs are."""
    M = MAP
    step = M["dot_gap"] * scale
    r = M["dot_r"] * scale
    carry = 0.0
    for pts in runs:
        for a, b in zip(pts, pts[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            t = carry
            while t <= L:
                x = a[0] + (b[0] - a[0]) * (t / L if L else 0)
                y = a[1] + (b[1] - a[1]) * (t / L if L else 0)
                d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD + (255,))
                t += step
            carry = t - L if L else carry


def place_label(d, fr, name, lon, lat, side, scale, live):
    M = MAP
    x, y = fr(lon, lat)
    r = M["city_r"] * scale
    col = GOLD if live else M["ghost"]
    d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,),
              outline=MAP["sea"] + (255,), width=max(1, round(scale)))
    f = font(INT_B if live else INT, max(11, round(M["label"] * scale)))
    pad = M["label_gap"] * scale + r
    anchors = {"n": ("ms", 0, -pad - f.size), "s": ("ms", 0, pad),
               "e": ("ls", pad, -f.size * 0.62), "w": ("rs", -pad, -f.size * 0.62),
               "ne": ("ls", pad * .7, -pad - f.size * .9), "nw": ("rs", -pad * .7, -pad - f.size * .9),
               "se": ("ls", pad * .7, pad * .3), "sw": ("rs", -pad * .7, pad * .3)}
    anc, dx, dy = anchors.get(side, anchors["e"])
    for off in ((-1, 0), (1, 0), (0, -1), (0, 1)):                 # a thin dark halo, so a name
        d.text((x + dx + off[0], y + dy + off[1] + f.size), name,  # over land still reads
               font=f, fill=MAP["sea"] + (220,), anchor=anc)
    d.text((x + dx, y + dy + f.size), name, font=f,
           fill=(WARM if live else DIM) + (255,), anchor=anc)


def tile(cue, fr, base, size, scale, dist, arrived):
    im = base.copy()
    d = ImageDraw.Draw(im)
    legs = cue["_legs"]
    runs, head = walk(legs, dist)
    if runs:
        dotted(d, runs, scale)
    for nm, lon, lat, side in cue.get("context", []):
        place_label(d, fr, nm, lon, lat, side, scale, live=False)
    for i, (nm, lon, lat, side) in enumerate(cue["places"]):
        place_label(d, fr, nm, lon, lat, side, scale, live=(i <= arrived))
    if head is not None and arrived < len(cue["places"]) - 1:
        r = MAP["head_r"] * scale
        d.ellipse([head[0] - r, head[1] - r, head[0] + r, head[1] + r], fill=GOLD + (255,))
    return im


def layout(cue, size, tmp):
    """The framing is identical on every frame of a motion file — shadow, hairline, caption, position.
    So it is built ONCE against a blank tile and each frame is just pasted into the hole. Framing a
    1920x1080 composite per frame (two Gaussian blurs and a justified caption) took longer than
    generating the clip it was illustrating."""
    blank = Image.new("RGBA", size, (0, 0, 0, 0))
    chrome = frame_it(cue, blank, tmp)
    w, h = size
    if cue.get("mode") == "full":
        pos = ((W - w) // 2, (H - h) // 2); mask = None
    else:
        P = PIP
        x = (W - P["margin"] - w) if P["side"] == "right" else P["margin"]
        pos = (x, P["top"] + P["band_h"] - h)
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=P["radius"], fill=255)
    return chrome, pos, mask


def frame_it(cue, im, tmp):
    """Hand the tile to the same framing the pictures use — corner shelf, or full frame."""
    p = os.path.join(tmp, "tile.png"); im.save(p)
    if cue.get("mode") == "full":
        return frame_full(p, cue.get("credit") or None, matte="keep", credit_below=False)
    return frame_picture(p, cue.get("credit") or None, matte="keep")


def prepare(cue):
    pts = list(cue["places"]) + list(cue.get("context", []))
    size = tile_size(cue.get("mode", "pip"), cue.get("aspect_ratio", MAP["aspect"]))
    scale = size[0] / 460.0                      # label and dot sizes are tuned at corner size
    fr = Frame(pts, size, cue.get("pad", MAP["pad"]))
    cue["_legs"] = path_points(fr, cue["places"], cue.get("bow", MAP["bow"]))
    return fr, size, max(scale, 0.85), base_tile(fr, size, max(scale, 0.85))


def leg_dists(cue):
    out, acc = [0.0], 0.0
    for pts in cue["_legs"]:
        acc += sum(seg_lengths(pts)); out.append(acc)
    return out


def render_steps(cue, out_dir):
    """One cumulative PNG per city — the line arrives on her word for that city."""
    fr, size, scale, base = prepare(cue)
    dists = leg_dists(cue)
    made = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, dist in enumerate(dists):
            im = frame_it(cue, tile(cue, fr, base, size, scale, dist, i), tmp)
            p = os.path.join(out_dir, f"{cue['id']}-{i+1}.png")
            im.save(p, optimize=True); made.append(p)
    return made


def render_motion(cue, out_dir, seconds=None):
    """One silent motion file — the dot travels and the line lays down behind it. A corner map is a .mov with an
    alpha channel; a full-frame map is an opaque .mp4."""
    fr, size, scale, base = prepare(cue)
    dists = leg_dists(cue)
    fps = MAP["fps"]
    seconds = seconds or float(str(cue.get("dur", "6s")).rstrip("s"))
    hold_in, hold_out = MAP["hold_in"], MAP["hold_out"]
    travel = max(seconds - hold_in - hold_out, 1.0)
    total_d = dists[-1] or 1.0
    n = int(round(seconds * fps))
    # A full-frame map replaces her, so it needs no alpha channel — and a full-frame qtrle file runs to hundreds of
    # megabytes, past what the bridge to dadtop will carry. Full frame is an ordinary H.264 .mp4 (S2E7's Tarshish map);
    # only a corner map needs the transparent .mov.
    full = cue.get("mode") == "full"
    ext, args = (("mp4", ("-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p")) if full
                 else (MAP["motion_ext"], tuple(MAP["motion_args"])))
    out = os.path.join(out_dir, f"{cue['id']}.{ext}")
    with tempfile.TemporaryDirectory() as tmp:
        chrome, pos, mask = layout(cue, size, tmp)
        for k in range(n):
            t = k / fps
            u = min(max((t - hold_in) / travel, 0.0), 1.0)
            u = u * u * (3 - 2 * u)                      # ease, so it does not start and stop hard
            dist = total_d * u
            arrived = max(i for i, dd in enumerate(dists) if dd <= dist + 1e-6)
            canvas = chrome.copy()
            t = tile(cue, fr, base, size, scale, dist, arrived)
            canvas.paste(t, pos, mask)
            canvas.save(os.path.join(tmp, f"f{k:04d}.png"))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
               "-i", os.path.join(tmp, "f%04d.png")] + list(args) + ["-an", out]
        subprocess.run(cmd, check=True)
    return out


def render_tile_video(cue, out_dir, seconds=None):
    """The map alone, opaque, at tile size — for laying over her footage and resizing into the corner
    by hand. No alpha, no 1920x1080 frame, nothing for a decoder to get wrong: the same path a
    Gemini-made clip takes into the edit. Set tile_video=True on the cue."""
    fr, size, scale, base = prepare(cue)
    dists = leg_dists(cue)
    fps = MAP["fps"]
    seconds = seconds or float(str(cue.get("dur", "6s")).rstrip("s"))
    hold_in, hold_out = MAP["hold_in"], MAP["hold_out"]
    travel = max(seconds - hold_in - hold_out, 1.0)
    total_d = dists[-1] or 1.0
    w, h = size
    out = os.path.join(out_dir, f"{cue['id']}-tile.mp4")
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(int(round(seconds * fps))):
            t = k / fps
            u = min(max((t - hold_in) / travel, 0.0), 1.0)
            u = u * u * (3 - 2 * u)
            dist = total_d * u
            arrived = max(i for i, dd in enumerate(dists) if dd <= dist + 1e-6)
            im = tile(cue, fr, base, size, scale, dist, arrived).convert("RGB")
            if im.width % 2 or im.height % 2:                      # h264 wants even dimensions
                im = im.crop((0, 0, im.width - im.width % 2, im.height - im.height % 2))
            im.save(os.path.join(tmp, f"f{k:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                        "-i", os.path.join(tmp, "f%04d.png"), "-c:v", "libx264", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-an", out], check=True)
    return out


def render(cue, out_dir):
    made = render_steps(cue, out_dir)

    def drop(name):                                       # never ship half a file from an encode that died
        p = os.path.join(out_dir, name)
        if os.path.exists(p): os.remove(p)
    if cue.get("tile_video"):
        try:
            made.append(render_tile_video(cue, out_dir))
        except Exception as e:
            drop(f"{cue['id']}-tile.mp4")
            print(f"  (no tile video for {cue['id']}: {e})")
    if cue.get("motion", True):
        try:
            made.append(render_motion(cue, out_dir))
        except Exception as e:                            # ffmpeg missing or unhappy: steps still ship, and the
            drop(f"{cue['id']}.{'mp4' if cue.get('mode') == 'full' else MAP['motion_ext']}")   # README says so
            print(f"  (no motion file for {cue['id']}: {e})")
    return made
