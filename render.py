#!/usr/bin/env python3
"""Render an episode's overlays (and frame its pictures) into an asset pack.

    python3 render.py episodes/S2E4.py                      → out/S2E4/overlays/*.png + README.md + MANIFEST.txt
    python3 render.py episodes/S2E4.py --pictures DIR       → also frames DIR/<picture-id>.* into overlays/
    python3 render.py episodes/S2E4.py --check frame.png    → out/S2E4/check-*.png (every file over her frame) and
                                                              check-phone-*.png (the same at an upright phone's size)

Every run builds into out/<code>.building/ and only replaces out/<code>/overlays/ once everything has rendered, so a
removed cue's file never ships again and a failed run leaves the last good pack alone (15 Oct 2026). MANIFEST.txt lists
exactly what this run made. The asset pack is what gets committed to dadtop: <PROJECT_FOLDER>\\<code>-assets\\
"""
import argparse, datetime, glob, hashlib, os, shutil, sys
from PIL import Image, ImageDraw
from episode import load
from style import OVERLAY_KINDS, MODES, RIGHTS, READ, INT
import overlays as O
from framing import frame_picture, frame_full, frame_strip
import maps, charts


def render(ep, out, pictures_dir=None):
    """Build into out/<code>.building, then swap overlays/ into place. Returns (files made, pictures waiting, notes)."""
    stage = out.rstrip("/\\") + ".building"
    shutil.rmtree(stage, ignore_errors=True)
    ov = os.path.join(stage, "overlays"); os.makedirs(ov)
    try:
        waiting, notes = build(ep, ov, pictures_dir)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)        # a failed run leaves the last good pack exactly as it was
        raise
    # Swap in only after everything rendered: what this run made replaces the old overlays/ entirely.
    os.makedirs(out, exist_ok=True)
    final = os.path.join(out, "overlays")
    if os.path.isdir(final): shutil.rmtree(final)
    shutil.move(ov, final)
    shutil.rmtree(stage, ignore_errors=True)
    for old in glob.glob(os.path.join(out, "check*.png")): os.remove(old)     # previews of the last pack, not this one
    files = sorted(os.listdir(final))
    open(os.path.join(out, "README.md"), "w").write(readme(ep, waiting, set(files)))
    open(os.path.join(out, "MANIFEST.txt"), "w").write(manifest(ep, final, files))
    return [os.path.join(final, f) for f in files], waiting, notes


def build(ep, ov, pictures_dir=None):
    """Render every overlay, map, chart and framed picture into `ov`. Returns (pictures waiting, notes)."""
    made, waiting, notes = [], [], []
    for c in ep.by_kind(*OVERLAY_KINDS):
        im = O.build(c)
        if isinstance(im, list):
            for n, fr in enumerate(im, 1):
                p = os.path.join(ov, f"{c['id']}-{n}.png"); O.save_quantized(fr, p); made.append(p)
        else:
            p = os.path.join(ov, f"{c['id']}.png"); O.save_quantized(im, p); made.append(p)
    for c in ep.by_kind("map"):
        made += maps.render(c, ov)
    for c in ep.by_kind("chart"):
        made += charts.render(c, ov)
    for c in ep.by_kind("picture"):
        src = None
        if c.get("file") and os.path.exists(c["file"]): src = c["file"]
        elif pictures_dir:
            hits = sorted(f for f in glob.glob(os.path.join(pictures_dir, c["id"] + ".*")) if not f.endswith(".txt"))
            src = hits[0] if hits else None
            if len(hits) > 1:      # used to take whichever the filesystem listed first, silently
                notes.append(f"{c['id']}: {len(hits)} files share the name ({', '.join(os.path.basename(h) for h in hits)}) — "
                             f"framed {os.path.basename(src)}; move the others to pictures\\raw\\alternates\\")
        if src:
            if c.get("mode") == "full":
                if c.get("arrow"):          # two frames: the picture, then the picture annotated
                    p1 = os.path.join(ov, f"{c['id']}-1.png")
                    frame_full(src, c.get("credit") or None, matte=c["matte"], crop=c.get("crop")).save(p1, optimize=True); made.append(p1)
                    p2 = os.path.join(ov, f"{c['id']}-2.png")
                    frame_full(src, c.get("credit") or None, arrow=c["arrow"], matte=c["matte"], crop=c.get("crop")).save(p2, optimize=True); made.append(p2)
                else:
                    p = os.path.join(ov, f"{c['id']}.png")
                    frame_full(src, c.get("credit") or None, matte=c["matte"], crop=c.get("crop")).save(p, optimize=True); made.append(p)
            elif c.get("mode") == "strip":
                p = os.path.join(ov, f"{c['id']}.png")
                frame_strip(src, c.get("credit") or None, matte=c["matte"], crop=c.get("crop")).save(p, optimize=True); made.append(p)
            else:
                p = os.path.join(ov, f"{c['id']}.png")
                frame_picture(src, c.get("credit") or None, matte=c["matte"], crop=c.get("crop")).save(p, optimize=True); made.append(p)
        else:
            waiting.append(c["id"])
    # A long verse is fitted smaller — on S2E3–S2E9 the densest cards were also the smallest type (READ in style.py).
    for c in ep.by_kind("scripture"):
        px, used, most = O.verse_size(c["text"], c["mode"])
        if px < READ["verse_min_px"]:
            notes.append(f"{c['id']}: the verse is set at {px} px, about {px * 393 / 1920:.1f} pt on an upright phone — "
                         f"shorten the excerpt (an ellipsis where she skips) or split it into two cards")
    return waiting, notes


def manifest(ep, folder, files):
    rows = []
    for f in files:
        data = open(os.path.join(folder, f), "rb").read()
        rows.append(f"overlays/{f}  {len(data):>9,} bytes  sha256 {hashlib.sha256(data).hexdigest()[:12]}")
    return (f"{ep.code} asset pack — rendered {datetime.date.today().isoformat()} — {len(files)} files\n"
            "Exactly what this render made. Anything in overlays\\ on dadtop that is not listed here is superseded:\n"
            "move it to _superseded\\ before unzipping (Expand-Archive keeps files the new zip doesn't have).\n\n"
            + "\n".join(rows) + "\n")


def readme(ep, waiting, files=None):
    m = ep.meta; n = ep.counts()
    files = files if files is not None else set()
    corr = "\n".join(f"- **{c[1]}** — she says \"{c[0]}\". {c[2]}" for c in ep.corrections) or "- none noted"
    def got(c):
        # Downloaded and framed by Claude (retrieved=…, S2E9): where it came from, and what the description owes.
        g = c.get("retrieved") if isinstance(c.get("retrieved"), dict) else None
        if not g: return ""
        return (f"\n  - downloaded {g.get('on') or ''} as `pictures/raw/{g.get('file') or c['id']}`"
                + (f" ({g['size']})" if g.get("size") else "") + f" — {c['source']}"
                + (f"\n  - **for the video description:** {g['owe']}" if g.get("owe") else ""))
    pics = "\n".join(f"- `{c['id']}` — {c['what']} · {RIGHTS[c['rights']][0]}" + (" · credit: " + c["credit"] if c.get("credit") else "")
                     + (f"\n  - {c['link']}" if c.get("link") else "")
                     + got(c)
                     + ("\n  - made, not found: copy the prompt from its card on the cue sheet (ChatGPT or Gemini, 16:9)" if c.get("prompt") else "")
                     for c in ep.by_kind("picture")) or "- none"
    def map_line(c):
        # Say only what this run actually made: a motion file that failed to render (ffmpeg missing or unhappy) used
        # to be listed anyway.
        motion = f"{c['id']}.mp4" if c.get("mode") == "full" else f"{c['id']}.mov"
        kind = "motion, full frame" if c.get("mode") == "full" else "motion, transparent"
        if motion in files:
            mot = f" and `{motion}` ({kind})"
        elif c.get("motion", True):
            mot = " — **no motion file this time** (it failed to render; see the render log), so place the steps"
        else:
            mot = ""
        tile = f" · `{c['id']}-tile.mp4` (opaque, corner size)" if f"{c['id']}-tile.mp4" in files else ""
        return f"- `{c['id']}-1.png … -{len(c['places'])}.png` (steps){mot}{tile} — {c.get('credit') or c['id']}"
    mp = "\n".join(map_line(c) for c in ep.by_kind("map")) or "- none"
    ch = "\n".join(f"- `{c['id']}-1.png … -{len(c['nodes'])}.png` — " + " → ".join(n["label"] for n in c["nodes"])
                    for c in ep.by_kind("chart")) or "- none"
    def attach(ids):
        return ", ".join(f"`{ep.reference(r)['file']}`" for r in ids if ep.reference(r))
    def ai_line(c):
        d = c.get("daring") if isinstance(c.get("daring"), dict) else None
        th = d["then"] if d and isinstance(d.get("then"), dict) else None
        if c.get("daring_only"):
            # Daring takes only (S2E9): the daring take is the clip, saved under the clip's own name.
            return (f"- `{c['id']}.mp4` — {c['title']} ({c['dur']}) · daring take"
                    + (" · attach " + attach(d.get("refs", ())) if d.get("refs") else "")
                    + ((f"\n  - shot 2: `{c['id']}-2.mp4`, cut to on “{th['cut_on']}”"
                        + (" · attach " + attach(th.get("refs", ())) if th.get("refs") else " · nothing attached"))
                       if th else ""))
        return (f"- `{c['id']}.mp4` — {c['title']} ({c['dur']})"
                + (" · attach " + attach(c.get("refs", ())) if c.get("refs") else "")
                + (f"\n  - daring take: `{c['id']}-daring.mp4`"
                   + (" · attach " + attach(d.get("refs", ())) if d.get("refs") else "")
                   + (f"\n  - daring take, shot 2: `{c['id']}-daring-2.mp4`, cut to on “{th['cut_on']}”"
                      + (" · attach " + attach(th.get("refs", ())) if th.get("refs") else " · nothing attached")
                      if th else "")
                   if d else ""))
    ai = "\n".join(ai_line(c) for c in sorted(ep.by_kind("ai"), key=lambda c: c.get("priority", 9))) or "- none"
    only_all = bool(ep.by_kind("ai")) and all(c.get("daring_only") for c in ep.by_kind("ai"))
    def ref_line(r):
        if r.get("standing"):
            # A standing character lives in his own folder in FaithForReal, not in the episode's (characters.py).
            return (f"- `{r['file']}` — {r['title']}. Standing character, in the FaithForReal folder — "
                    + ("made; attach it from there." if r.get("made")
                       else "not made yet: the two prompts that make his whole set are on the cue sheet."))
        return (f"- `{r['file']}` — {r['title']}. "
                + ("Already made — keep it in the episode folder under this name." if r.get("made")
                   else "Make this before any clip; the prompt is on the cue sheet."))
    refs = ("\n".join(ref_line(r) for r in ep.references)
            + "\n\nA reference is attached, not used as a start frame: Ingredients in Flow, an attachment in the Gemini app.\n"
            + ("Every clip here is a daring take, so each one attaches the front view with the view from behind, and the\n"
               "head-and-shoulders view where his face is the shot. Flow takes three images; four go to the Gemini app.\n\n"
               if only_all else
               "The safe takes get the costume reference from behind, because they never show his face; the daring takes,\n"
               "where they exist, get the front view as well, so his face holds from clip to clip.\n\n")) if ep.references else ""
    wait = ("\n\n**Still waiting for pictures:** " + ", ".join(f"`{w}`" for w in waiting)
            + f" — drop the files into `pictures\\raw\\` as `<id>.jpg` or `.png` and ask for a re-render.") if waiting else ""
    # Say only what applies to this pack: the kinetic, map and chart notes appear when the episode has one,
    # and the clip instructions follow the format the cards are written for (S2E6: every clip text to video).
    kin = ("\nKinetic text (`*-1.png … *-n.png`) is one cue: cross-fade six frames between steps, each step on its word.\n"
           if n.get("kinetic") else "")
    maps_block = f"""
### Maps — already rendered, nothing to fetch
{mp}

Each map ships twice. The numbered PNGs are cumulative steps: put each one on its own scene so the
line reaches a city as she says it, cross-fading six frames between them, exactly like kinetic text.
The `.mov` is the same map animating on its own clock, with a transparent background — one file,
dropped on one scene, if you would rather not cut it to her words. It is QuickTime Animation (lossless
RGBA), because a VP9 WebM of the same thing imported into Descript as a black rectangle.
""" if ep.by_kind("map") else ""
    charts_block = f"""
### Charts — already rendered, nothing to fetch
{ch}

Same placement as kinetic text: one PNG per rank, each on its own scene, six-frame cross-fade between them.
""" if ep.by_kind("chart") else ""
    if only_all:
        ai_how = ("Every clip is a daring take, text to video with reference images. Copy the whole prompt from its card on the\n"
                  "cue sheet — the guards for that shot and the silent, one-take block are already on the end — attach the\n"
                  "images the card names, and generate in the Gemini app (or Flow's Ingredients, which takes three images),\n"
                  "16:9. Take three or four outputs, keep the one that holds together, and save it here as `<id>.mp4`.")
    elif all(c.get("frames", "none") == "none" for c in ep.by_kind("ai")):
        ai_how = ("Every clip is text to video. Copy the whole prompt from its card on the cue sheet — the guards for that shot and\n"
                  "the silent, one-take block are already on the end — paste it into Google Flow as text to video, 16:9, take two\n"
                  "outputs, keep the one with more life in it, and save it here as `<id>.mp4`.")
    else:
        ai_how = ("Prompts are on the cue sheet with the style block appended to every copy button. Generate all the start frames in one\n"
                  "ChatGPT conversation so it holds the look; make the videos in Google Flow (Frames to Video) with the start frame.")
    return f"""# {m['code']} — asset pack

Overlays for **{m['title']}** — {m.get('runtime') or 'runtime tbc'}. Cue sheet: {m.get('artifact') or '(published when the transcript lands)'}

Every file in `overlays/` is a **1920×1080 PNG with transparency**. Drag the folder into Descript's media panel once,
then work down the cue sheet: click the phrase to copy it, Ctrl-F it in the script view, add a scene break a word
early, drop the file on that scene, set the layer's In/Out animation to a 0.6 s fade.

Two things that are not obvious the first time:

- **A punch-in is two scene breaks, not one.** Each punch cue gives two phrases — one where the frame tightens and
  one where it releases. Break at both, set the scene between them to the tighter framing, and leave the rest as shot.
  With only the first break the punch runs on to wherever the next break happens to be.
- **The clips come back eight seconds long, whatever the cue asked for.** The duration on an `ai` cue is how long it
  should be ON SCREEN — trim to it from the strongest few seconds. If a clip needs to keep a length that does not
  match the words underneath it, detach it into its own sequence so the two are not tied together.

## What the modes mean
- **Band** — {MODES['band']}
- **Dim** — {MODES['dim']}
- **Cut** — {MODES['cut']}
- **Picture** — {MODES['pip']}{chr(10) + "- **Picture across the bottom** — " + MODES['strip'] if any(c.get("mode") == "strip" for c in ep.by_kind("picture")) else ""}
- **Punch-in** — {MODES['punch']}

One thing on screen at a time. Nothing sits on top of anything else.

## What is in this pack
{n.get('scripture',0)+n.get('kinetic',0)} scripture · {n.get('stat',0)+n.get('figures',0)} stats · {n.get('quote',0)} quotes · {n.get('name',0)+n.get('names',0)} names · {n.get('timeline',0)} explainers · {n.get('picture',0)} pictures · {n.get('ai',0)} AI clips · {n.get('punch',0)} punch-in candidates
{kin}
### Pictures (framed into `overlays/pic-*.png` once the raw files are in `pictures/raw/`)
{pics}{wait}
{maps_block}{charts_block}
### AI clips — generate these into `ai/`
{refs}{ai}

{ai_how}

## Corrections — fix these in the captions too
{corr}

## Colours
Text `#F5EFE4`, accent `#E2AA82`. Lifted so they survive over video; the gold sits between her curtain and her table wood.
"""


def contact_sheet(ep, out, frame_path):
    """Every PNG this run made — each kinetic, map and chart step, both frames of an arrowed picture — composited over
    her frame in cue order. check-N.png at a third of full size; check-phone-N.png at 393 px wide, an upright phone's
    width in points, which is how small the captions and references really come out there. (Until 15 Oct 2026 this
    was one sheet of at most eight files.)"""
    frame = Image.open(frame_path).convert("RGBA").resize((1920, 1080), Image.LANCZOS)
    order = {c["id"]: i for i, c in enumerate(ep.cues)}

    def key(f):
        base = os.path.splitext(os.path.basename(f))[0]
        cid = max((i for i in order if base == i or base.startswith(i + "-")), key=len, default=None)
        return (order.get(cid, len(order)), base)
    files = sorted(glob.glob(os.path.join(out, "overlays", "*.png")), key=key)
    pages = []
    for name, tw, cols, rows, lab in (("check", 640, 3, 4, 20), ("check-phone", 393, 4, 6, 14)):
        th, per = tw * 9 // 16, cols * rows
        try:
            f_lab = O.font(INT, lab)
        except Exception:
            f_lab = None
        for start in range(0, len(files), per):
            chunk = files[start:start + per]
            sheet = Image.new("RGB", (cols * tw, ((len(chunk) + cols - 1) // cols) * (th + lab + 10)), (20, 20, 20))
            d = ImageDraw.Draw(sheet)
            for i, f in enumerate(chunk):
                x, y = (i % cols) * tw, (i // cols) * (th + lab + 10)
                tile = Image.alpha_composite(frame, Image.open(f).convert("RGBA")).resize((tw, th), Image.LANCZOS)
                sheet.paste(tile.convert("RGB"), (x, y))
                d.text((x + 4, y + th + 4), os.path.basename(f), fill=(200, 195, 185), font=f_lab)
            p = os.path.join(out, f"{name}-{start // per + 1}.png"); sheet.save(p); pages.append(p)
    return pages


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("episode"); ap.add_argument("--out"); ap.add_argument("--pictures"); ap.add_argument("--check")
    a = ap.parse_args()
    ep = load(a.episode)
    for w in ep.warnings: print("WARN ", w)
    for e in ep.errors: print("ERROR", e)
    if ep.errors: sys.exit(1)
    out = a.out or os.path.join("out", ep.code)
    made, waiting, notes = render(ep, out, a.pictures)
    print(f"{ep.code}: wrote {len(made)} files to {out}/overlays" + (f"; waiting for pictures: {', '.join(waiting)}" if waiting else ""))
    for note in notes: print("NOTE ", note)
    if a.check:
        pages = contact_sheet(ep, out, a.check)
        print("check sheets:", ", ".join(os.path.basename(p) for p in pages) or "none — nothing rendered")
