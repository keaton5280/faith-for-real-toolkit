#!/usr/bin/env python3
"""Load and validate an episode file (episodes/S2E4.py).

An episode file is plain Python with:
    EPISODE      dict   code, title, runtime, descript{...}, assets_folder, artifact, lede
    CUES         list   one dict per cue — see episodes/_template.py for every field
    SECTIONS     list   (first_cue_id, title, subtitle) — groups the cue sheet
    CORRECTIONS  list   (heard, correct, note) — names she mispronounces, for captions
    NOT_PICTURED list   (who, why) — the pictures the policy says no to, so the no is visible
    NOTES        list   (title, text) — callouts for the bottom of the cue sheet

load(path) fills defaults, validates, and returns an Episode with .errors and .warnings.
"""
import collections, math, os, re, types
from style import (KINDS, OVERLAY_KINDS, DEFAULT_DUR, QUOTAS, RIGHTS, PROJECT_FOLDER, HERO_CLIP,
                   PUNCH_DUR, BREATH, CLIP_DELIVERED, CLIP_FRAMES_DEFAULT, GUARD_LINES, READ, FIRST_MINUTE)

REQUIRED = {
    "scripture": ("text", "ref"), "stat": ("hero", "sub", "src"), "figures": ("rows", "src"),
    "quote": ("text", "who"), "name": ("name", "role"), "names": ("names",),
    "timeline": ("rows", "between"), "kinetic": ("steps",),
    "ai": ("title", "image", "video"), "picture": ("what", "source", "rights"), "punch": ("why",),
    "map": ("places",), "chart": ("nodes",),
}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DUR_RE = re.compile(r"^(\d+)s$")


class Episode:
    def __init__(self, path, meta, cues, sections, corrections, not_pictured, notes, references=None):
        self.path, self.meta, self.cues = path, meta, cues
        self.sections, self.corrections, self.not_pictured, self.notes = sections, corrections, not_pictured, notes
        self.references = list(references or [])      # character references for clips — see REF_LEAD in style.py
        self.errors, self.warnings = [], []

    def reference(self, rid):
        return next((r for r in self.references if r.get("id") == rid), None)

    @property
    def code(self): return self.meta["code"]

    @property
    def state(self):
        anchored = [bool(c.get("anchor")) for c in self.cues]
        if not anchored or not any(anchored): return "plan"
        if all(anchored): return "cut"
        return "partial"

    def by_kind(self, *kinds): return [c for c in self.cues if c["kind"] in kinds]

    def counts(self):
        return collections.Counter(c["kind"] for c in self.cues)


def secs(dur):
    m = DUR_RE.match(str(dur)); return int(m.group(1)) if m else None


def runtime_minutes(rt):
    try:
        p = [int(x) for x in str(rt).split(":")]
        return (p[0] * 60 + p[1] + p[2] / 60) if len(p) == 3 else (p[0] + p[1] / 60)
    except Exception:
        return None


def load(path):
    # Compiled from the source every time, never from __pycache__: check_anchors --fix rewrites the file and reloads it
    # within the same second, and a same-length fix (a capital letter) would otherwise come back from the stale .pyc.
    mod = types.ModuleType("episode_data"); mod.__file__ = path
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), mod.__dict__)
    meta = dict(getattr(mod, "EPISODE"))
    cues = [dict(c) for c in getattr(mod, "CUES")]
    ep = Episode(path, meta, cues,
                 list(getattr(mod, "SECTIONS", [])), list(getattr(mod, "CORRECTIONS", [])),
                 list(getattr(mod, "NOT_PICTURED", [])), list(getattr(mod, "NOTES", [])),
                 [dict(r) for r in getattr(mod, "REFERENCES", [])])
    E, Wn = ep.errors.append, ep.warnings.append

    # Standing characters (characters.py, added 2026-10-07): a clip may attach their reference ids without the episode
    # declaring them — their images are made once, live in their own folder on dadtop, and serve every episode.
    try:
        from characters import standing_refs
        standing = standing_refs()
    except ImportError:
        standing = {}
    declared = {r.get("id") for r in ep.references}
    for c in cues:
        ids = list(c.get("refs", ()))
        d = c.get("daring")
        if isinstance(d, dict):
            ids += list(d.get("refs", ()))
            if isinstance(d.get("then"), dict): ids += list(d["then"].get("refs", ()))
        for rid in ids:
            if rid not in declared and rid in standing:
                ep.references.append(dict(standing[rid])); declared.add(rid)

    # Character references: one image of a recurring person, attached to the clips he appears in so he is
    # the same man in all of them. A reference, not a start frame — see REF_LEAD in style.py.
    for r in ep.references:
        rid = r.get("id") or "?"
        if not ID_RE.match(str(rid)): E(f"reference {rid}: id must be a lowercase slug")
        for f in ("name", "prompt"):
            if not r.get(f): E(f"reference {rid}: needs {f!r}")
        r.setdefault("who", "man"); r.setdefault("title", f"{r.get('name', rid)} — the reference image")
        r.setdefault("file", f"ai/ref-{rid}.png"); r.setdefault("note", "")
        r.setdefault("made", False)          # True once Keaton has made it — the card then says where to save it
        r.setdefault("poss", "her" if r["who"] in ("woman", "girl") else "his")

    for k in ("code", "title"):
        if not meta.get(k): E(f"EPISODE.{k} is missing")
    meta.setdefault("runtime", None); meta.setdefault("descript", {}); meta.setdefault("lede", "")
    # What we expect the cut to run to, from the script's word count, before a real runtime exists.
    # Quotas scale off this so a long episode is not judged against half-hour numbers all through
    # the planning phase; it is never displayed as if it were a real runtime.
    meta.setdefault("planned_runtime", None)
    meta.setdefault("sensitive", None)   # a one-line reason when the episode involves real people who were harmed
    meta.setdefault("assets_folder", PROJECT_FOLDER + "\\" + f"{meta.get('code', 'S?E?')}-assets")
    # How a clip prompt treats a person whose reference images are attached (added for S2E9). "named": a few words for
    # who he is, plus only what this scene changes — the images carry his look, and his full description is on his card
    # for a clip made without them. "described": he is described in full in every prompt, so deleting the lead sentence
    # turns the card into plain text to video. Episodes before S2E9 have no key and were written "described"; the
    # template sets "named".
    meta.setdefault("people_in_prompts", "described")
    if meta["people_in_prompts"] not in ("named", "described"):
        E(f"EPISODE.people_in_prompts must be 'named' or 'described', not {meta['people_in_prompts']!r}")

    seen = collections.Counter(c.get("id") for c in cues)
    for i, c in enumerate(cues):
        tag = c.get("id") or f"cue #{i+1}"
        k = c.get("kind")
        if not c.get("id"): E(f"{tag}: no id"); continue
        if not ID_RE.match(c["id"]): E(f"{tag}: id must be a lowercase slug (a-z, 0-9, hyphens)")
        if seen[c["id"]] > 1: E(f"{tag}: duplicate id")
        if k not in KINDS: E(f"{tag}: unknown kind {k!r}"); continue
        # A clip may be a daring take and nothing else (added for S2E9, at Keaton's request: "only do daring takes"):
        # daring=dict(image=…, video=…) with no safe image or video. It is the clip, saved as ai/<id>.mp4.
        daring_only = (k == "ai" and isinstance(c.get("daring"), dict)
                       and c.get("image") in (None, "") and c.get("video") in (None, ""))
        for f in REQUIRED[k]:
            if daring_only and f in ("image", "video"): continue
            if c.get(f) in (None, "", [], ()): E(f"{tag}: {k} needs {f!r}")
        if k == "ai":
            c["daring_only"] = daring_only
            if daring_only and c.get("refs"):
                E(f"{tag}: a daring-only clip carries its references in daring=dict(refs=…) — there is no safe take for refs=…")
        c.setdefault("mode", KINDS[k][2]); c.setdefault("dur", DEFAULT_DUR[k])
        c.setdefault("note", ""); c.setdefault("anchor", None); c.setdefault("beat", None)
        c.setdefault("tc", None); c.setdefault("approx", None)
        if k in OVERLAY_KINDS and c["mode"] not in ("band", "dim"): E(f"{tag}: mode must be band or dim")
        if not (c["anchor"] or c["beat"]): E(f"{tag}: needs a beat (script sentence) or an anchor (transcript phrase)")
        if c["anchor"] and len(c["anchor"].split()) < 4: Wn(f"{tag}: anchor is under four words — Ctrl-F will hit it more than once")
        d = secs(c["dur"])
        # A duration the spacing check cannot read used to count as zero seconds there, so a typo ("9", "9 sec") let
        # two things share the frame unnoticed. "—" is a punch-in's default: it holds PUNCH_DUR unless given a dur.
        if c["dur"] != "—" and not d:
            E(f"{tag}: dur {c['dur']!r} — write whole seconds with an s, like \"8s\"")
        if k == "ai":
            if c["mode"] not in ("cut", "pipclip"):
                E(f"{tag}: an ai clip is mode 'cut' (replaces her) or 'pipclip' (laid over her and resized into the corner)")
            c.setdefault("frames", CLIP_FRAMES_DEFAULT)
            c.setdefault("guards", ())
            bad = [g for g in c["guards"] if g not in GUARD_LINES and len(str(g).split()) < 4]
            if bad: E(f"{tag}: unknown guard(s) {', '.join(bad)} — use one of {', '.join(GUARD_LINES)}, "
                      f"or write the line out in full")
            c.setdefault("priority", 9); c.setdefault("period", True)
            c.setdefault("hero_clip", False)
            c.setdefault("refs", ())
            for rid in c["refs"]:
                if not ep.reference(rid):
                    E(f"{tag}: refs names {rid!r}, which is not in REFERENCES")
            if c["refs"] and c["frames"] != "none":
                E(f"{tag}: a reference goes with text to video (frames='none') — a start frame already fixes "
                  f"what everything looks like, so the two would fight")
            if c["frames"] not in ("none", "start", "start+end"): E(f"{tag}: frames must be 'none' (text to video), 'start' or 'start+end'")
            if c["frames"] == "start+end" and not c.get("end_image"): E(f"{tag}: start+end needs end_image (what the last frame looks like)")
            # A daring-only clip (S2E9) is made in the Gemini app, which hands back ten seconds a shot, and a two-shot
            # one (daring then=…) is on screen for both shots — the S2E9 séance runs 19 s from the scream to the bow.
            cap = (20 if isinstance((c.get("daring") or {}).get("then"), dict) else 10) if daring_only else 8
            if d and d > cap:
                E(f"{tag}: {c['dur']} — over the " + ("eight-second maximum of a clip" if cap == 8 else
                  f"{cap} seconds the Gemini app hands back for " + ("two shots" if cap == 20 else "one")))
            elif d and d > 6 and not c.get("hero_clip") and not daring_only:   # a daring take uses the full length
                Wn(f"{tag}: {c['dur']} — clips over six seconds drift; ask for 4–6 s and hold the cut if you need longer, "
                   f"or make this the hero clip, where the full eight seconds is allowed")
            # The daring take — the same beat with the house rules about faces, camera, animals and motion lifted.
            # It sits in the same slot as the safe take, so it is validated here and never counted as a clip of its own.
            dg = c.get("daring")
            if dg is not None:
                if not isinstance(dg, dict) or not dg.get("image") or not dg.get("video"):
                    E(f"{tag}: daring needs dict(image=…, video=…) — the shot and the action, like the safe take")
                else:
                    dg.setdefault("refs", ()); dg.setdefault("guards", ()); dg.setdefault("note", "")
                    dg.setdefault("dur", "8s")
                    for rid in dg["refs"]:
                        if not ep.reference(rid):
                            E(f"{tag}: daring refs names {rid!r}, which is not in REFERENCES")
                    badg = [g for g in dg["guards"] if g not in GUARD_LINES and len(str(g).split()) < 4]
                    if badg: E(f"{tag}: daring has unknown guard(s) {', '.join(badg)}")
                    if "faces" in dg["guards"]:
                        Wn(f"{tag}: the daring take carries the faces guard — that is the safe take's job; the daring "
                           f"take exists to show him")
                    dd = secs(dg["dur"])
                    if not dd: E(f"{tag}: daring dur {dg['dur']!r} — write whole seconds with an s, like \"8s\"")
                    elif dd > 10: E(f"{tag}: daring {dg['dur']} — Veo returns eight seconds and the Gemini app ten")
                    # then=dict(…) — a second shot the edit cuts to on `cut_on` (added for S2E7), so a dangerous
                    # moment can happen in the cut: the moment before with his face, the moment after without him.
                    th = dg.get("then")
                    if th is not None:
                        if not isinstance(th, dict) or not th.get("image") or not th.get("video") or not th.get("cut_on"):
                            E(f"{tag}: daring then= needs dict(image=…, video=…, cut_on=…) — the second shot, and the "
                              f"word in her line the edit cuts to it on")
                        else:
                            th.setdefault("refs", ()); th.setdefault("guards", ()); th.setdefault("note", "")
                            th.setdefault("dur", "8s")
                            for rid in th["refs"]:
                                if not ep.reference(rid):
                                    E(f"{tag}: daring then refs names {rid!r}, which is not in REFERENCES")
                            badt = [g for g in th["guards"] if g not in GUARD_LINES and len(str(g).split()) < 4]
                            if badt: E(f"{tag}: daring then has unknown guard(s) {', '.join(badt)}")
                            if th["cut_on"] not in (c.get("beat") or ""):
                                Wn(f"{tag}: daring then cuts on {th['cut_on']!r}, which is not in the beat — the cut "
                                   f"belongs on her word for it")
                            td = secs(th["dur"])
                            if not td: E(f"{tag}: daring then dur {th['dur']!r} — write whole seconds with an s, like \"8s\"")
                            elif td > 10: E(f"{tag}: daring then {th['dur']} — Veo returns eight seconds and the Gemini app ten")
        elif c.get("daring") is not None:
            E(f"{tag}: daring only means something on an ai cue")
        if k == "chart":
            c.setdefault("credit", ""); c.setdefault("motion", False)
            if c["mode"] not in ("pip", "full"): E(f"{tag}: a chart is mode 'pip' (over her shoulder) or 'full' (whole frame)")
            if len(c.get("nodes", [])) < 2: E(f"{tag}: a chart needs at least two ranks — the reveal is the whole point")
            for nd in c.get("nodes", []):
                if not isinstance(nd, dict) or not nd.get("label"):
                    E(f"{tag}: each rank is dict(label=…, sub=…, icons=n)")
                elif int(nd.get("icons", 1)) > 60:
                    Wn(f"{tag}: {nd['label']} has {nd['icons']} figures — over about sixty they stop being countable "
                       f"and turn into texture; say the number in the sub line instead")
        if k == "map":
            c.setdefault("credit", ""); c.setdefault("context", []); c.setdefault("motion", True)
            if c["mode"] not in ("pip", "full"): E(f"{tag}: a map is mode 'pip' (over her shoulder) or 'full' (whole frame)")
            if len(c.get("places", [])) < 2: E(f"{tag}: a map needs at least two places to travel between")
            for pl in c.get("places", []) + list(c.get("context", [])):
                if not (isinstance(pl, (list, tuple)) and len(pl) == 4):
                    E(f"{tag}: each place is (name, lon, lat, label side) — e.g. (\"Tyre\", 35.20, 33.27, \"ne\")")
                elif not (-180 <= pl[1] <= 180 and -90 <= pl[2] <= 90):
                    E(f"{tag}: {pl[0]} — coordinates are (lon, lat) in that order, and {pl[1]}, {pl[2]} is not on Earth")
        if k == "picture":
            c.setdefault("credit", ""); c.setdefault("file", None); c.setdefault("search", c.get("what")); c.setdefault("aspect", "")
            # `link` (added for S2E7): the exact page when it is already known — a museum object page, a 3D model, a
            # Commons file. The card then says "open →" and goes straight there instead of running a search.
            c.setdefault("link", None)
            if c["link"] and not str(c["link"]).startswith("https://"): E(f"{tag}: link is a full https:// address")
            c.setdefault("arrow", None); c.setdefault("matte", "trim"); c.setdefault("crop", None)
            # `retrieved` (added for S2E9): the picture has been downloaded and framed — a short line saying when, how
            # big, and anything the description owes (a photographer's credit). The card then says where the file came
            # from instead of how to find it; `link` should be the exact file page it came from.
            c.setdefault("retrieved", None)
            if c["retrieved"] and not c["link"]: Wn(f"{tag}: retrieved, but no link to the exact file it came from")
            if c["crop"] is not None:
                cr = c["crop"]
                if not (isinstance(cr, (list, tuple)) and len(cr) == 4):
                    E(f"{tag}: crop is (left, top, right, bottom) as fractions of the source, 0-1")
                elif not (all(0 <= v <= 1 for v in cr) and cr[0] < cr[2] and cr[1] < cr[3]):
                    E(f"{tag}: crop {tuple(cr)} is not a box — each side is 0-1, left < right and top < bottom")
            if c["matte"] not in ("keep", "trim", "knockout", "paper"):
                E(f"{tag}: matte is 'trim' (default — crop a uniform white or black mount), "
                  f"'knockout' (drop that mount out to transparency, for an object photographed on one), "
                  f"'paper' (set a cut-out scan back on a page, S2E9) or 'keep' (do neither)")
            if c["mode"] not in ("pip", "full", "strip"):
                E(f"{tag}: a picture is mode 'pip' (over her shoulder), 'full' (whole frame) or 'strip' (across the "
                  f"bottom of the frame, for a frieze or a panorama)")
            if c["arrow"]:
                if c["mode"] != "full": E(f"{tag}: an arrow only means something on a full-frame picture")
                a = c["arrow"]
                if not isinstance(a, dict) or "at" not in a:
                    E(f"{tag}: arrow needs at=(x, y) as fractions of the picture, 0-1 from the top left")
                else:
                    x, y = a["at"]
                    if not (0 <= x <= 1 and 0 <= y <= 1): E(f"{tag}: arrow at=({x}, {y}) must be fractions between 0 and 1")
                    if a.get("provisional"): Wn(f"{tag}: the arrow target is provisional — it has to be checked against the "
                                                f"file once it is downloaded, with `python3 arrowgrid.py {c['id']}`")
            r = c.get("rights")
            if r not in RIGHTS: E(f"{tag}: rights must be one of {', '.join(RIGHTS)}")
            elif RIGHTS[r][1] == "never": E(f"{tag}: '{RIGHTS[r][0]}' — the policy does not allow this picture")
            elif RIGHTS[r][1] == "avoid": Wn(f"{tag}: news-agency image — three seconds, credited, and expect a possible claim; is there a PD or official alternative?")
            elif RIGHTS[r][1] == "label" and "reconstruction" not in (c.get("credit") or "").lower():
                E(f"{tag}: a generated reconstruction has to say so on screen — put the word 'reconstruction' "
                  f"in the credit line, or change rights to the class the real picture belongs to")
            if r in ("official", "frame") and not c.get("credit"): Wn(f"{tag}: credit the rights holder on screen")
            # A reconstruction is made, not found: give it the prompt (added for S2E7) so the card has a copy button.
            if r == "gen" and not c.get("prompt") and not c.get("file"):
                Wn(f"{tag}: a generated reconstruction with no prompt=… — the card has nothing to copy; write the image "
                   f"prompt, or point file= at the picture if it is already made")
            if c.get("prompt") and r != "gen":
                E(f"{tag}: prompt=… means the picture is generated — set rights='gen', which puts 'reconstruction' in the caption")
            # The caption is justified to the picture's own width, so its LENGTH is a design
            # decision, not just an editorial one. Roughly one character per nine pixels of
            # picture at the house size; well outside that and it either sets too small or
            # cannot reach the measure at all.
            cr = c.get("credit") or ""
            if cr and c["mode"] == "strip" and len(cr) > 110:
                Wn(f"{tag}: the caption is {len(cr)} characters — under a strip it is one line, flush left; cut it to "
                   f"about a hundred")
            if cr and c["mode"] == "pip":
                if len(cr) < 22:
                    Wn(f"{tag}: the caption is {len(cr)} characters — too short to fill the width of "
                       f"the picture, so it will sit under it looking clipped. Say a little more")
                elif len(cr) > 58:
                    Wn(f"{tag}: the caption is {len(cr)} characters — it will wrap to two lines or set "
                       f"small under the picture. Cut it to about fifty")
            if d and d > 6 and c["mode"] != "full":
                Wn(f"{tag}: pictures over six seconds start to look like a slideshow — unless it is mode 'full', "
                   f"where the whole point is that there is time to look at it")
        if k == "kinetic" and len(c.get("steps", [])) < 2: E(f"{tag}: kinetic needs at least two steps")
        if c.get("hero_clip") and k != "ai": E(f"{tag}: hero_clip=True only means something on an ai cue")
        if k == "punch":
            # A punch-in is two scene breaks in Descript, not one: the frame tightens at `anchor`
            # and releases at `out`. Without the second phrase he has to guess where it ends, and
            # a punch that runs a sentence too long stops reading as emphasis.
            c.setdefault("out", None)
            if not c["out"]:
                Wn(f"{tag}: no `out` phrase — a punch-in needs a second anchor for where the frame "
                   f"releases, because that is a second scene break in Descript")
        elif c.get("out"):
            E(f"{tag}: `out` only means something on a punch cue")

    # one thing at a time
    by_anchor = collections.defaultdict(list)
    for c in cues:
        if c.get("anchor"): by_anchor[c["anchor"]].append(c["id"])
    for a, ids in by_anchor.items():
        if len(ids) > 1: Wn(f"same anchor on {', '.join(ids)} — one thing on screen at a time; move one to the next sentence")

    # one thing at a time, part two: nothing may still be on screen when the next thing arrives.
    # Only checkable once the cues carry timecodes, so it is silent on a plan-state episode.
    timed = [c for c in cues if c.get("tc")]
    if timed:
        def tsec(t):
            try:
                h, m, s2 = (int(x) for x in t.split(":")); return h * 3600 + m * 60 + s2
            except Exception:
                E(f"[{t}] is not a timecode — write it HH:MM:SS"); return None
        stamped = []
        for c in timed:
            t = tsec(c["tc"])
            if t is None: continue
            if c["kind"] == "punch":
                d = secs(c["dur"]) or PUNCH_DUR             # a long punch can say how long it holds: dur="6s"
            elif c["kind"] == "ai":
                d = max(secs(c["dur"]) or 0, CLIP_DELIVERED)   # what lands on the timeline untrimmed
            else:
                d = secs(c["dur"]) or 0
            stamped.append((t, t + d, c))
        stamped.sort(key=lambda r: r[0])
        for (s1, e1, a), (s2, e2, b) in zip(stamped, stamped[1:]):
            gap = s2 - e1
            if gap < 0:
                E(f"[{b['id']}] starts at {b['tc']} while {a['id']} is still up until "
                  f"{a['tc']}+{a['dur'] if a['kind'] != 'punch' else str(PUNCH_DUR)+'s'} — "
                  f"two things on screen at once. Move one, or shorten the first")
            elif gap < BREATH:
                Wn(f"[{b['id']}] arrives {gap}s after {a['id']} clears — under {BREATH}s of daylight "
                   f"they read as one continuous graphic")
        for (s1, e1, a), (s2, e2, b) in zip(stamped, stamped[1:]):
            if a["tc"] == b["tc"]:
                Wn(f"[{a['id']}] and [{b['id']}] share a timecode — one thing on screen at a time")

    used = {rid for c in cues if c.get("kind") == "ai" for rid in c.get("refs", ())}
    used_daring = {rid for c in cues if c.get("kind") == "ai" and isinstance(c.get("daring"), dict)
                   for rid in tuple(c["daring"].get("refs", ()))
                   + tuple((c["daring"].get("then") or {}).get("refs", ()) if isinstance(c["daring"].get("then"), dict) else ())}
    for r in ep.references:
        if r.get("id") not in used | used_daring:
            Wn(f"reference {r.get('id')}: declared but no clip uses it — give the clips he appears in refs=(\"{r.get('id')}\",)")
        # A reference that shows the face belongs on daring takes only: on a safe take it invites the model to turn
        # him round and show it, which is the one thing the safe take is for not doing.
        if r.get("id") in used and re.search(r"\b(face|portrait|smil|looking at the camera|front view)", r.get("prompt", ""), re.I) \
                and not re.search(r"face is (turned away|hidden)|no face", r.get("prompt", ""), re.I):
            Wn(f"reference {r.get('id')}: a safe take attaches a reference that shows the face — use the costume "
               f"reference from behind on safe takes, and keep the front view for the daring ones")

    # quotas
    n = ep.counts()
    mins = runtime_minutes(meta.get("runtime")) or runtime_minutes(meta.get("planned_runtime")) or 30.0
    scale = mins / 30.0
    dims = sum(1 for c in cues if c["kind"] in OVERLAY_KINDS and c["mode"] == "dim")
    if dims > round(QUOTAS["dim"] * scale): Wn(f"{dims} dim overlays — the ceiling is about {round(QUOTAS['dim']*scale)} for {meta.get('runtime') or '30 min'}; dims only work if they are rare")
    heroes = [c for c in cues if c["kind"] == "ai" and c.get("hero_clip")]
    if len(heroes) > HERO_CLIP["per_episode"]:
        E(f"{len(heroes)} hero clips ({', '.join(h['id'] for h in heroes)}) — the budget is "
          f"{HERO_CLIP['per_episode']} per episode; the exception only means anything while it is rare")
    ordinary = n["ai"] - len(heroes)          # the hero is an extra spend, not one of the four-to-seven
    lo, hi = QUOTAS["ai"]                      # a ceiling only — no warning below it since 15 Oct 2026 (style.py)
    if ordinary > round(hi * scale): Wn(f"{ordinary} ordinary AI clips — more than {round(hi*scale)} stops feeling sparing")
    if n["picture"] > round(QUOTAS["picture"][1] * scale): Wn(f"{n['picture']} pictures — over {round(QUOTAS['picture'][1]*scale)} and it turns into a slideshow")
    plo, phi = QUOTAS["punch"]
    if n["punch"] > round(phi * scale): Wn(f"{n['punch']} punch-in candidates — keep it to {plo}–{phi}; they only read as emphasis if they are rare")
    early = [c for c in cues if c["kind"] in ("ai", "picture", "kinetic") and c.get("tc") and c["tc"] < "00:05:00"]
    if ep.state != "plan" and not early: Wn("nothing moves in the first five minutes — no clip, picture or kinetic text — and that is where retention is decided")
    def at(t):
        try:
            h, m_, s_ = (int(x) for x in str(t).split(":")); return h * 3600 + m_ * 60 + s_
        except Exception:
            return None
    first = [c for c in cues if c.get("tc") and at(c["tc"]) is not None and at(c["tc"]) < FIRST_MINUTE]
    if ep.state != "plan" and not first:
        Wn(f"nothing changes on screen in the first {FIRST_MINUTE} s — not even a punch-in — and the 2 Oct review found "
           f"46–60% of viewers gone by 1:00 on every episode")

    # reading load (added 15 Oct 2026): a card is only useful if it can be read while she keeps talking.
    def longwords(s):
        return [w for w in re.findall(r"[a-z0-9']+", (s or "").lower().replace("’", "'")) if len(w) > 3]
    prev = None
    for c in cues:
        if c["kind"] not in ("scripture", "quote", "timeline"): continue
        txt = (" ".join(str(r[1]) for r in c.get("rows", []) if len(r) > 1) if c["kind"] == "timeline"
               else str(c.get("text") or ""))
        again, prev = txt == prev, txt
        d = secs(c["dur"])
        if not d or again: continue              # a highlight step on a verse already up asks for no new reading
        card, said = longwords(txt), set(longwords(c.get("beat") or c.get("anchor")))
        along = sum(w in said for w in card) / len(card) if card else 0
        if along >= READ["along"]: continue      # she reads it out word for word, so the eye follows the ear
        limit = READ["cps_paraphrase"] if along >= READ["paraphrase"] else READ["cps"]
        cps = len(txt) / d
        if cps <= limit: continue
        Wn(f"[{c['id']}] {len(txt)} characters in {c['dur']} is {cps:.1f} a second — over the {limit} a viewer can read "
           + ("while she paraphrases it" if limit == READ["cps_paraphrase"] else "while she says something else")
           + f". Cut it to the clause she is making, split it, or hold it {math.ceil(len(txt) / limit)}s")
    return ep


if __name__ == "__main__":
    import sys
    ep = load(sys.argv[1])
    print(f"{ep.code} — {ep.meta['title']} — state: {ep.state} — {len(ep.cues)} cues")
    for k, v in sorted(ep.counts().items()): print(f"  {k:10} {v}")
    for w in ep.warnings: print("WARN ", w)
    for e in ep.errors: print("ERROR", e)
    sys.exit(1 if ep.errors else 0)
