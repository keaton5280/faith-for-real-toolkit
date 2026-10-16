#!/usr/bin/env python3
"""Lint AI clip prompts for the things that seed bad generations.

The one rule: the video prompt animates what is already in the start frame and
never introduces anything. Everything else here is a known failure mode with a
known trigger word. ERROR blocks the cue sheet; WARN prints on the prompt card
so it is read before generating, not after; INFO is advice.

    python3 lint_prompts.py episodes/S2E4.py
"""
import re, sys
from style import DEPICT_CHRIST_IN_CLIPS

NEG = re.compile(r"\b(no|not|never|nobody|no one|nothing|without|nor|neither)\b", re.I)

# (key, pattern, message) — matched in both prompts unless negated within 40 chars before
RISK = [
    ("hands",   r"\b(writing|writes|handwriting|holding|holds|picks? up|grips?|gripping|dips?|dipping|pours?|pouring|turn(s|ing)? (a|the) page|ties|tying|carv(es|ing)|threads?|fingers?)\b",
     "hands doing fine work are the first thing to break — extra fingers, pens through paper. Objects only, or hands at rest and out of focus"),
    ("face",    r"\b(faces?|expressions?|smiles?|smiling|looks? (at|into|toward) (the )?camera|portrait|close-?up of (a|the|an) (man|woman|figure|traveler|person|face))\b",
     "a face — generated faces go uncanny, and it breaks her rule. Backs, distance, silhouettes"),
    ("jesus",   r"\b(jesus|christ)\b",
     "Jesus is in this shot"),
    ("text",    r"\b(text|letters|lettering|inscription|inscribed|written words|legible|signage|writing on|glyphs?)\b",
     "legible text becomes gibberish glyphs — scrolls rolled or turned away, 'no legible text'"),
    ("crowd",   r"\b(crowd of (hundreds|thousands)|hundreds|thousands|dozens of people|throng|multitude|packed with)\b",
     "big crowds merge and duplicate — at most four people near camera, a crowd only far back and small"),
    ("animal",  r"\b(horses?|donkeys?|camels?|dogs?|sheep|goats?|cattle|oxen|birds?|animals?|mules?)\b",
     "animals get extra legs and sliding gaits — leave them out, or static and distant in the start frame"),
    ("vehicle", r"\b(carts?|chariots?|wagons?|carriages?)\b(?! ruts)",
     "carts and chariots arrive with nothing pulling them — leave them out"),
    ("bolt",    r"\b(lightning bolts?|bolts? of lightning|zigzag|thunderbolts?)\b",
     "a drawn bolt comes out as a cartoon — 'a light pulses from inside the cloud'"),
    ("camera",  r"\b(pans?|panning|orbits?|orbiting|dolly|dollies|tracking shot|handheld|crane|whip|zooms? out|rack focus|drone|aerial|fly-?over|sweeps?)\b",
     "camera moves warp geometry — locked off, or a push-in of a few percent"),
    ("speed",   r"\b(suddenly|quickly|rapidly|fast|races?|rushes?|rushing|sprints?|sprinting|bursts?|flashes|whips?)\b",
     "speed words smear — one slow motion, 'unhurried'"),
]
MODERN = r"\b(wristwatch|watch|eyeglasses|glasses|zipper|plastic|jeans|t-shirt|phone|cars?|trucks?|electric|neon|asphalt|concrete)\b"

# nouns that count as "a thing" when the motion prompt has them and the picture does not
THINGS = set("""person people man woman child children boy girl figure figures traveler soldier priest guard family crowd hand hands
horse donkey camel dog sheep goat ox oxen bird birds animal cart chariot wagon boat ship sail
fire flame smoke torch lamp candle lantern water river sea wave rain snow cloud lightning
tree trees rock rocks stone stones wall walls door gate window tower tent building house temple column pillar arch bridge road path
table chair bed bench basket bowl cup jar jug pot cloth robe cloak sandal sandals staff rope chain scroll book codex pen ink coin sword spear helmet
bread wine fish net boat oar wheel banner flag curtain veil crown throne altar candle bell""".split())

BODY = set("arm arms head heads foot feet leg legs shoulder shoulders back knee knees hand hands eye eyes hair".split())
PERSON = re.compile(r"\b(traveler|figure|family|families|man|woman|people|companions?|crowd|townspeople|children|child|soldiers?|men|women)\b", re.I)

SYN = {"dusty": "dust", "fiery": "fire", "smoky": "smoke", "sandy": "sand", "cloudy": "cloud", "flame": "fire", "flames": "fire",
       "burning": "fire", "glow": "light", "glowing": "light", "lit": "light", "sunlight": "light", "lamplight": "light", "firelight": "fire",
       "walls": "wall", "gate": "wall",
       "figure": "person", "figures": "person", "people": "person", "townspeople": "person", "companion": "person",
       "companions": "person", "traveler": "person", "travelers": "person", "watcher": "person"}

STILL = re.compile(r"(do(es)? not move|don't move|stays? (still|where|dark|put)|stay in place|locked off|remains? still|do(es)? not change|holds? still|keeps? still|nobody (turns|moves)|does not turn)", re.I)
MOTION_VERBS = re.compile(r"\b(walks?|walking|rises?|rising|lifts?|drifts?|churns?|spreads?|climbs?|grows?|pulses?|breathes?|curls?|flickers?|sways?|ripples?|falls?|settles?|shifts?|moves?|lowers?|raises?|steps?|burns?|flows?|glows?|brightens?|fades?)\b", re.I)


def stem(w):
    w = w.lower().strip("“”\"'’‘.,;:!?()[]—-")
    if not w: return w
    if w in SYN: return SYN[w]
    if w.endswith("ies") and len(w) > 4: return w[:-3] + "y"
    if w.endswith("ing") and len(w) > 5: w = w[:-3]
    elif w.endswith("ed") and len(w) > 4: w = w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3: w = w[:-1]
    return SYN.get(w, w)


def clauses(text):
    return [c for c in re.split(r"[,.;:—()]+", text) if c.strip()]


def affirmative(text):
    """The text with every negated clause removed — 'no cart, no animal' is a guard, not a cart."""
    return " ".join(c for c in clauses(text) if not NEG.search(c))


def tokens(text):
    return {stem(w) for w in re.findall(r"[A-Za-z][A-Za-z’'-]*", text)} - {""}


def negated(text, start):
    return bool(NEG.search(text[max(0, start - 40):start]))


def hits(text, pattern):
    return [m.group(0) for m in re.finditer(pattern, text, re.I) if not negated(text, m.start())]


def jesus_row(word, refs, jesus_refs, guards=()):
    """Jesus may be in a clip when the story calls for it (DEPICT_CHRIST_IN_CLIPS, Keaton 2026-10-07). What the
    linter checks is that he is the same man every time: his reference images attached, and no guard that says
    he is not there."""
    if not DEPICT_CHRIST_IN_CLIPS:
        return ("ERROR", f"jesus: '{word}' — depicting Jesus in a clip is switched off in style.py")
    if "christ" in guards:
        return ("WARN", f"jesus: '{word}' — the prompt puts him in the shot and the christ guard says he is not there; "
                        f"drop one of them")
    if not any(r in jesus_refs for r in refs):
        return ("WARN", f"jesus: '{word}' — he is in this shot with no reference image attached, so he will be a "
                        f"different man from every other clip. Declare him in REFERENCES (ids jesus-…) and attach "
                        f"the back view on a safe take, the front and back views on a daring one")
    return ("INFO", f"jesus: '{word}' — in the shot, with his references attached. Call him Jesus and say only what this "
                    f"scene changes; his description, on his card, is for a take made without the images")


def lint_cue(c, jesus_refs=()):
    """Return [(level, message)] for one ai cue."""
    out = []
    img, vid = c.get("image", ""), c.get("video", "")
    if not img or not vid: return [("ERROR", "image and video prompts are both required")]

    t2v = c.get("frames") == "none"      # text to video: there is no start frame to protect
    # 1. the rule — things the motion prompt names that the picture does not contain
    have = tokens(img)
    new = tokens(affirmative(vid)) - have
    if PERSON.search(img): new -= BODY
    things = sorted(w for w in new if w in THINGS)
    if things and not t2v:
        out.append(("WARN", "the video prompt names things that are not in the image prompt: " + ", ".join(things)
                    + " — anything not in the start frame gets hallucinated in mid-clip. Put it in the picture or take it out"))

    # 2. risk words
    hero = bool(c.get("hero_clip"))
    LIFTED = {"crowd"}          # what the hero budget allows; see HERO_CLIP in style.py
    both = img + " " + vid
    for key, pat, msg in RISK:
        h = hits(both, pat)
        if h:
            if key == "jesus":
                out.append(jesus_row(h[0], c.get("refs", ()), jesus_refs, c.get("guards", ())))
            elif hero and key in LIFTED:
                out.append(("INFO", f"{key}: '{h[0]}' — allowed on the hero clip, and the reason it is the hero. "
                                    "Still keep every figure anonymous: seen from above, from behind or at a distance, no face readable"))
            else:
                out.append(("WARN", f"{key}: '{h[0]}' — {msg}"))
    if re.search(r"\bhands?\b", affirmative(img), re.I):
        out.append(("INFO", "hands are in the start frame — keep them at rest and out of focus; the video prompt must not move them"))
    if c.get("period", True):
        h = hits(both, MODERN)
        if h: out.append(("WARN", f"modern object in a period scene: '{h[0]}'"))

    # 3. structure of the motion prompt — frames-to-video craft, meaningless without a start frame
    if t2v:
        out.append(("INFO", "text to video — the start-frame rules are off. Write it as a shot: subject, action, "
                            "camera, light, in positive language. What is appended to every prompt is only the four "
                            "universals (one take, realism, no text, silent); anything this particular shot must not "
                            "show goes in its own guards=()"))
        if c.get("refs"):
            out.append(("INFO", "with a reference image — it fixes what he looks like, not where the camera is, and a "
                                "reference pulls a model toward showing its character up close. Keep the shot saying where "
                                "he is in the frame and which way he faces, and keep the faces guard on"))
            if "faces" not in c.get("guards", ()):
                out.append(("WARN", "a clip with a character reference and no faces guard — the reference is exactly what "
                                    "tempts the model to turn him round"))
        return out
    if not STILL.search(vid):
        out.append(("WARN", "the video prompt never says what stays still — the model will move everything a little"))
    last = re.split(r"(?<=[.!?])\s+", vid.strip())[-1]
    if not NEG.search(last):
        out.append(("WARN", "close the video prompt with what must not appear ('No hand enters, nothing is added to the frame.')"))
    moving = [s for s in re.split(r"(?<=[.!?])\s+", vid) if MOTION_VERBS.search(s) and not NEG.search(s)]
    if len(moving) > 3 and not hero:
        out.append(("WARN", f"{len(moving)} sentences of motion — name one primary motion and let the rest be secondary or still"))
    elif len(moving) > 3 and hero:
        out.append(("INFO", f"{len(moving)} sentences of motion — allowed here, but they still have to be able to happen "
                            "at once in one place; check the result for motions that ignore each other"))
    img_last = re.split(r"(?<=[.!?])\s+", img.strip())[-1]
    if not NEG.search(img_last) and not re.search(r"nothing else", img, re.I):
        out.append(("INFO", "end the image prompt with what is not there ('Nothing else in frame. No people, no hands.')"))

    # 4. frames and length
    m = re.match(r"(\d+)s", str(c.get("dur", "")))
    if m and int(m.group(1)) > 8: out.append(("ERROR", "over eight seconds — split it or hold the last frame in the edit"))
    if c.get("frames") == "start+end":
        if not c.get("end_image"): out.append(("ERROR", "start+end frames but no end_image described"))
        else:
            extra = sorted(w for w in (tokens(affirmative(c["end_image"])) - have) if w in THINGS)
            if extra: out.append(("WARN", "the end frame adds things the start frame lacks (" + ", ".join(extra) + ") — same camera and objects; change only light or position"))
    return out


# ── what the generators refuse (added for S2E7) ─────────────────────────
# Not a failure of the model but a refusal by the product around it. The Gemini app turned down Jonah thrown
# overboard twice: "I can't make videos of real people in situations like that" — the photographic face in the
# attached reference reads as a real person — and then, told he was generated, "I can't make videos that could relate
# to dangerous situations". What sets it off is a person in mortal danger on screen: thrown, drowning, sinking,
# swallowed, flung. With a face reference attached that is a WARN; without one it is INFO, because a wide shot of a
# small figure may still get through. Arguing in the chat changes nothing. The way round it is the cut — the moment
# before, with his face, and the moment after, without him (daring then=dict(…)).
PERIL = (r"\b(violent(ly)?|terrified|terror|drown\w*|hurl\w*|heaves? (him|her|them)|throws? (him|her|them)|"
         r"toss(es)? (him|her|them)|flung|tumbl\w*|plung\w*|gone under|goes under|sink(s|ing)?|cough\w*|chok\w*|"
         r"gasp\w*|struggl\w*|swallow\w*|devour\w*|blood\w*|wound\w*|kill\w*|corpse|lifeless)\b")
SOMEONE = re.compile(r"\b(he|him|his|she|her|they|them|man|woman|men|women|figure|person|people|sailors?|soldiers?|"
                     r"child|children|boy|girl)\b", re.I)


def shows_face(ref):
    """Does this reference image show the face? Same test episode.py uses for the safe-take warning."""
    pr = ref.get("prompt", "")
    return bool(re.search(r"\b(face|portrait|smil|looking at the camera|front view)", pr, re.I)) \
        and not re.search(r"face is (turned away|hidden)|no face", pr, re.I)


def peril(text, face=False, names=()):
    """(level, message) when the prompt puts a person in mortal danger on screen, else None."""
    h = hits(text, PERIL)
    if not h: return None
    if not (SOMEONE.search(text) or any(re.search(r"\b" + re.escape(n) + r"\b", text) for n in names)): return None
    if face:
        return ("WARN", f"refusal bait — '{h[0]}' with a face reference attached. The Gemini app refuses a recognisable "
                        f"person in danger: it reads the reference as a real person ('real people in situations like "
                        f"that'), then calls the shot a dangerous situation. Show the moment before with his face and the "
                        f"moment after without him, and let the cut do the rest (daring then=…)")
    return ("INFO", f"a person in danger on screen ('{h[0]}') — a generator may refuse it as a 'dangerous situation'. If it "
                    f"does, use the moment after instead, with nobody in the water")


def _people(ep):
    refs = getattr(ep, "references", None) or []
    return {r["id"] for r in refs if shows_face(r)}, tuple(sorted({r.get("name") for r in refs if r.get("name")}))


def _jesus_refs(ep):
    """Reference ids that are Jesus — by name, or by an id that starts jesus-."""
    refs = getattr(ep, "references", None) or []
    return {r["id"] for r in refs if str(r.get("name", "")).lower() in ("jesus", "christ", "jesus of nazareth")
            or str(r.get("id", "")).startswith("jesus")}


def _descriptions(ep):
    """(name, description) by reference id, for every attached person who has a description — the standing
    characters do (characters.py)."""
    refs = getattr(ep, "references", None) or []
    return {r["id"]: (r.get("name"), r.get("description")) for r in refs if r.get("description")}


def described_twice(text, ids, descs):
    """With EPISODE people_in_prompts="named" (S2E9 on), a prompt names the people whose images it attaches and says
    only what the scene changes. Pasting a full description as well says everything twice, and wherever the words and
    the pictures disagree it gives the model two answers. Any sentence of the description found verbatim counts."""
    rows, seen = [], set()
    for rid in ids:
        name, desc = descs.get(rid, (None, None))
        if not desc or name in seen: continue
        seen.add(name)
        if any(len(x) >= 40 and x in text for x in (t.strip() for t in re.split(r"(?<=\.)\s+", desc))):
            rows.append(("WARN", f"{name}'s description is pasted into a prompt that attaches his images — name him and say "
                                 f"only what this scene changes; the description on his card is for a clip made "
                                 f"without the images"))
    return rows


def _named(ep):
    return getattr(ep, "meta", {}).get("people_in_prompts") == "named"


def lint(ep):
    faces, names = _people(ep)
    jr = _jesus_refs(ep)
    descs = _descriptions(ep) if _named(ep) else {}
    out = {}
    for c in ep.by_kind("ai"):
        if c.get("daring_only"):        # no safe take to lint — the daring take is linted by lint_daring_all
            out[c["id"]] = []
            continue
        rows = lint_cue(c, jr)
        p = peril(c.get("image", "") + " " + c.get("video", ""), any(r in faces for r in c.get("refs", ())), names)
        if p: rows.append(p)
        rows += described_twice(c.get("image", "") + " " + c.get("video", ""), c.get("refs", ()), descs)
        out[c["id"]] = rows
    return out


# The daring take (daring=dict(…) on an ai cue) lifts the rules that exist because models fail at things — faces,
# hands, animals, camera moves, speed — so those are reported as what the take is attempting, not as warnings. What
# the channel itself will not show is still checked exactly as on the safe take: legible text and modern objects.
# Jesus is not on that list (Keaton, 2026-10-07); a daring take with him in it gets the same reference check.
HELD_RISKS = {"text": "WARN"}


def lint_shot(d, faces=(), names=(), jesus_refs=()):
    """Lint one daring shot — the daring take itself, or the second shot it cuts to (then=…)."""
    out, taking = [], []
    both = d.get("image", "") + " " + d.get("video", "")
    for key, pat, msg in RISK:
        h = hits(both, pat)
        if not h: continue
        if key == "jesus":
            out.append(jesus_row(h[0], d.get("refs", ()), jesus_refs, d.get("guards", ())))
        elif key in HELD_RISKS:
            out.append((HELD_RISKS[key], f"{key}: '{h[0]}' — {msg}"))
        else:
            taking.append(f"{key} ('{h[0]}')")
    h = hits(both, MODERN)
    if h: out.append(("WARN", f"modern object in a period scene: '{h[0]}'"))
    if taking:
        out.append(("INFO", "daring on purpose — this take attempts " + ", ".join(taking)
                    + ". Take three or four outputs and keep the one where it holds together"))
    p = peril(both, any(r in faces for r in d.get("refs", ())), names)
    if p: out.append(p)
    return out


def lint_daring(c, faces=(), names=(), jesus_refs=()):
    d = c.get("daring")
    return lint_shot(d, faces, names, jesus_refs) if isinstance(d, dict) else []


def lint_daring_then(c, faces=(), names=(), jesus_refs=()):
    d = c.get("daring")
    return lint_shot(d["then"], faces, names, jesus_refs) if isinstance(d, dict) and isinstance(d.get("then"), dict) else []


def lint_daring_all(ep):
    faces, names = _people(ep)
    jr = _jesus_refs(ep)
    descs = _descriptions(ep) if _named(ep) else {}
    out = {}
    for c in ep.by_kind("ai"):
        if not c.get("daring"): continue
        out[c["id"]] = lint_daring(c, faces, names, jr)
        d = c["daring"]
        if isinstance(d, dict):
            out[c["id"]] += described_twice(d.get("image", "") + " " + d.get("video", ""), d.get("refs", ()), descs)
    return out


def lint_daring_then_all(ep):
    faces, names = _people(ep)
    jr = _jesus_refs(ep)
    descs = _descriptions(ep) if _named(ep) else {}
    out = {}
    for c in ep.by_kind("ai"):
        if not (isinstance(c.get("daring"), dict) and c["daring"].get("then")): continue
        th = c["daring"]["then"]
        out[c["id"]] = lint_daring_then(c, faces, names, jr) + described_twice(
            th.get("image", "") + " " + th.get("video", ""), th.get("refs", ()), descs)
    return out


def worst(report):
    lv = {"ERROR": 3, "WARN": 2, "INFO": 1}
    return max((lv[l] for r in report.values() for l, _ in r), default=0)


if __name__ == "__main__":
    from episode import load
    ep = load(sys.argv[1])
    rep = lint(ep)
    for cid, rows in rep.items():
        if not rows: print(f"{cid:22} ok"); continue
        for lvl, msg in rows: print(f"{cid:22} {lvl:5} {msg}")
    drep = lint_daring_all(ep)
    for cid, rows in drep.items():
        for lvl, msg in rows: print(f"{cid + ' (daring)':22} {lvl:5} {msg}")
    trep = lint_daring_then_all(ep)
    for cid, rows in trep.items():
        for lvl, msg in rows: print(f"{cid + ' (daring 2)':22} {lvl:5} {msg}")
    sys.exit(1 if max(worst(rep), worst(drep), worst(trep)) == 3 else 0)
