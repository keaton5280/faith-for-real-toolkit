#!/usr/bin/env python3
"""Fetch the coastline the map cues draw on, clipped to the world the show lives in.

Natural Earth's 10m land polygons are 10 MB; almost all of it is Greenland and the Pacific.
This downloads them once, keeps only the rings that touch the Mediterranean box, simplifies
them to about the accuracy a 450-pixel map can show, and writes geo/med.json (a few hundred
kilobytes). Idempotent — skips if the file is already there.

    python3 setup_geo.py
"""
import json, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "geo", "med.json")
SRC = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_land.geojson"
BOX = (-12.0, 26.0, 46.0, 50.0)        # lon min, lat min, lon max, lat max — Gibraltar to the Euphrates
TOL = 0.006                             # degrees; about 600 m, well under one pixel at these scales


def simplify(pts, tol):
    """Douglas-Peucker, iterative."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        ax, ay = pts[i]; bx, by = pts[j]
        dx, dy = bx - ax, by - ay
        n2 = dx * dx + dy * dy
        worst, wi = 0.0, None
        for k in range(i + 1, j):
            px, py = pts[k]
            if n2 == 0:
                d = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / n2))
                d = ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5
            if d > worst: worst, wi = d, k
        if wi is not None and worst > tol:
            keep[wi] = True; stack += [(i, wi), (wi, j)]
    return [p for p, k in zip(pts, keep) if k]


def main():
    if os.path.exists(OUT):
        print("geo/med.json present"); return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print("fetching Natural Earth 10m land …")
    raw = json.loads(urllib.request.urlopen(SRC, timeout=180).read().decode())
    lo_x, lo_y, hi_x, hi_y = BOX
    rings = []
    for f in raw["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            for ring in poly:                      # outer ring and any holes, all drawn as outlines
                xs = [c[0] for c in ring]; ys = [c[1] for c in ring]
                if max(xs) < lo_x or min(xs) > hi_x or max(ys) < lo_y or min(ys) > hi_y:
                    continue
                r = simplify([(round(c[0], 4), round(c[1], 4)) for c in ring], TOL)
                if len(r) >= 4:
                    rings.append(r)
    json.dump({"box": BOX, "rings": rings}, open(OUT, "w"))
    print(f"wrote {OUT} — {len(rings)} rings, {os.path.getsize(OUT)//1024} KB")


if __name__ == "__main__":
    main()
