#!/usr/bin/env python3
"""Render a downloaded picture at full frame with a coordinate grid, so an arrow target can be
read off it. The numbers along the top and left are the fractions to put in arrow=dict(at=(x, y)).

    python3 arrowgrid.py pic-rembrandt-stephen                 # uses pictures/raw/<id>.*
    python3 arrowgrid.py pic-rembrandt-stephen 0.62 0.41 135   # preview an actual arrow too
    python3 arrowgrid.py pic-bruegel-saul --pictures DIR       # the raw files staged somewhere else (S2E9)
"""
import glob, sys, os
from framing import frame_full

args = sys.argv[1:]
pics = os.path.join("pictures", "raw")
if "--pictures" in args:
    i = args.index("--pictures")
    if i + 1 >= len(args):
        sys.exit(__doc__)
    pics = args[i + 1]; del args[i:i + 2]
if not args:
    sys.exit(__doc__)
cid = args[0]
hits = [f for f in glob.glob(os.path.join(pics, cid + ".*")) if not f.endswith(".txt")]
if not hits:
    sys.exit(f"no {os.path.join(pics, cid)}.* — download it first")
arrow = None
if len(args) >= 3:
    arrow = dict(at=(float(args[1]), float(args[2])),
                 from_deg=float(args[3]) if len(args) > 3 else 225, label="Saul")
os.makedirs("out", exist_ok=True)
out = os.path.join("out", f"{cid}-grid.png")
frame_full(hits[0], "grid — not for the edit", arrow=arrow, grid=True).convert("RGB").save(out)
print("wrote", out, "— read the target off the grid, then set arrow=dict(at=(x, y))")
