#!/usr/bin/env python3
"""Chart cues — the shape of an organisation, drawn, revealed one rank at a time.

Her scripts keep stopping to explain who outranks whom: a tribune and the garrison under him,
a centurion and his hundred, a cohort inside a legion. Said out loud that is an abstraction the
viewer has to hold in their head. Drawn, it is one glance — a figure, a line down, and a block
of figures underneath.

A chart renders as cumulative PNG steps, exactly like kinetic text and like a map: the top rank
is on screen while she names it, and the rank below arrives on the word for it. Framed by the
picture code, so it sits in the same corner on the same shelf with the same caption (or full
frame). Nothing here is a card or a panel floating over her — it is the same over-the-shoulder
object every other picture is.

The figures are drawn, not photographed, and that is the point: the picture policy allows a
diagram Claude can draw when the point is a shape rather than a likeness. A generated Roman
officer would be a guess at a face; this is a count and a chain of command, which is what she
actually said.
"""
import math, os, tempfile
from PIL import Image, ImageDraw
from style import CHART, WARM, GOLD, DIM, INT, INT_B
from overlays import font
from maps import frame_it, tile_size          # maps.py owns the shared framing helpers


def figure(d, x, y, h, colour, crest=False, scale=1.0):
    """One standing figure: head, shoulders, body. Geometric on purpose — a count, not a portrait."""
    head_r = h * 0.17
    d.ellipse([x - head_r, y, x + head_r, y + head_r * 2], fill=colour)
    if crest:                                    # the officer's transverse crest, so rank reads at a glance
        cw, ch = head_r * 2.4, head_r * 0.8
        d.polygon([(x - cw / 2, y + head_r * 0.25), (x, y - ch), (x + cw / 2, y + head_r * 0.25)], fill=colour)
    top = y + head_r * 2 + h * 0.07
    bw = h * 0.46
    d.polygon([(x - bw / 2, y + h), (x - bw * 0.42, top), (x + bw * 0.42, top), (x + bw / 2, y + h)], fill=colour)


def grid(n, cols):
    rows = math.ceil(n / cols)
    return [(i % cols, i // cols) for i in range(n)], rows


def draw(cue, size, upto):
    """The chart with ranks 0..upto drawn.

    The whole assembly is measured first and centred once, so a rank NEVER moves between steps —
    the only difference from one PNG to the next is that the rank below has arrived. That is what
    makes the six-frame cross-fade read as an arrival rather than as a jump.
    """
    C = CHART
    w, h = size
    im = Image.new("RGBA", size, C["ground"] + (255,))
    d = ImageDraw.Draw(im)
    nodes = cue["nodes"]

    def measure(s):
        fl = font(INT_B, max(11, round(C["label"] * s)))
        fs = font(INT, max(10, round(C["sub"] * s)))
        blocks = []
        for i, node in enumerate(nodes):
            n = int(node.get("icons", 1))
            fh = C["figure_big"] * s if n == 1 else C["figure_small"] * s
            cols = min(n, int(node.get("cols", C["cols"])))
            cells, rows = grid(n, cols)
            gapx = fh * C["gap_x"]; gapy = fh * C["gap_y"]
            block_h = (rows - 1) * gapy + fh
            label_h = C["label_gap"] * s + fl.size * 1.25 + (fs.size * 1.6 if node.get("sub") else 0)
            blocks.append(dict(node=node, n=n, fh=fh, cells=cells, cols=cols, rows=rows,
                               gapx=gapx, gapy=gapy, block_h=block_h, label_h=label_h))
        conn = C["connector"] * s
        total = sum(b["block_h"] + b["label_h"] for b in blocks) + conn * (len(blocks) - 1)
        return blocks, total, conn, fl, fs

    # Fit before drawing: whatever the ranks and the wording, the assembly is scaled until it sits
    # inside the card with its padding. A clipped label is a bug, and a chart is exactly the kind of
    # thing that grows a line when somebody edits the words.
    s = w / 460.0                                # tuned at corner size
    pad = C["pad"] * s
    blocks, total, conn, fl, fs = measure(s)
    if total > h - 2 * pad:
        s *= (h - 2 * pad) / total
        pad = C["pad"] * s
        blocks, total, conn, fl, fs = measure(s)
    y = max(pad, (h - total) / 2)

    for i, b in enumerate(blocks):
        node = b["node"]
        if i > upto:
            break
        x0 = w / 2 - (b["cols"] - 1) * b["gapx"] / 2
        colour = (GOLD if i == 0 else C["rank"]) + (255,)
        for (cx, cy) in b["cells"]:
            figure(d, x0 + cx * b["gapx"], y + cy * b["gapy"], b["fh"], colour,
                   crest=node.get("crest", i == 0))
        ly = y + b["block_h"] + C["label_gap"] * s
        d.text((w / 2, ly), node["label"].upper(), font=fl,
               fill=(WARM if i == 0 else DIM) + (255,), anchor="ma")
        if node.get("sub"):
            d.text((w / 2, ly + fl.size * 1.35), node["sub"], font=fs, fill=C["subcol"] + (255,), anchor="ma")
        y += b["block_h"] + b["label_h"]
        if i < len(blocks) - 1:
            if i < upto:                          # the line only appears with the rank it points at
                d.line([(w / 2, y + conn * 0.18), (w / 2, y + conn * 0.82)],
                       fill=C["rule"] + (255,), width=max(2, round(2.5 * s)))
            y += conn
    return im


def render(cue, out_dir):
    size = tile_size(cue.get("mode", "pip"), cue.get("aspect_ratio", CHART["aspect"]))
    made = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(len(cue["nodes"])):
            im = frame_it(cue, draw(cue, size, i), tmp)
            p = os.path.join(out_dir, f"{cue['id']}-{i+1}.png")
            im.save(p, optimize=True); made.append(p)
    return made
