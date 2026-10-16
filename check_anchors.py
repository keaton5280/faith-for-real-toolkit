#!/usr/bin/env python3
"""Verify every cue anchor against the actual transcript.

An anchor is what Keaton pastes into Descript's Ctrl-F. It has to be text she
really said, and it has to occur exactly once, or the search lands on the wrong
sentence and the asset goes in the wrong place. Neither of those is a judgement
call, so it is checked here rather than trusted to care.

Matching ignores punctuation and case, because Descript punctuates differently
from a script. When an anchor matches loosely but not exactly, the transcript's
own wording is reported so the anchor can be replaced with it verbatim.

    python3 check_anchors.py episodes/S2E4.py transcript.txt           # report
    python3 check_anchors.py episodes/S2E4.py transcript.txt --fix     # rewrite anchors to her exact words, re-check
    python3 check_anchors.py episodes/S2E4.py transcript.txt --strict  # the gate before publishing a cue sheet:
                                                                       # exits 1 unless every phrase is exact and unique
"""
import re, sys, unicodedata

FOLD = {"‘": "'", "’": "'", "“": '"', "”": '"',
        "–": " ", "—": " ", "…": " ", " ": " "}


# Descript's export drops a [HH:MM:SS] marker into the middle of a sentence every
# thirty seconds. Ctrl-F in the app searches the words, not the markers, so an anchor
# that happens to straddle one is fine there and would fail here. Strip them first.
MARKER = re.compile(r"\[\d{1,2}:\d{2}(?::\d{2})?\]")


def strip_markers(s):
    return MARKER.sub(" ", s)


def normalize_map(s):
    """Return (normalized text, index map back into s)."""
    out, idx, prev_space = [], [], True
    for i, ch in enumerate(s):
        c = FOLD.get(ch, ch)
        # a comma or period between digits is a separator, not a word break: 2,600 == 2600
        if c in ",." and 0 < i < len(s) - 1 and s[i - 1].isdigit() and s[i + 1].isdigit():
            continue
        if c.isalnum() or c == "'":
            out.append(c.lower()); idx.append(i); prev_space = False
        elif not prev_space:
            out.append(" "); idx.append(i); prev_space = True
    while out and out[-1] == " ":
        out.pop(); idx.pop()
    return "".join(out), idx


def occurrences(hay, needle):
    at, i = [], hay.find(needle)
    while i != -1:
        at.append(i); i = hay.find(needle, i + 1)
    return at


def check(ep, transcript):
    """Return [(level, cue_id, message)] plus a dict of suggested verbatim anchors."""
    norm, idx = normalize_map(transcript)
    rows, fixes, positions = [], {}, []
    probes = []
    for c in ep.cues:
        if c.get("anchor"): probes.append((c, "anchor", c["anchor"]))
        if c.get("out"):    probes.append((c, "out", c["out"]))
        # Also Ctrl-F targets (S2E9): the phrase a two-shot clip cuts to its second shot on, and the phrase a picture's
        # arrow arrives on. Checked the same way, but never rewritten by --fix, which only knows top-level fields.
        th = (c.get("daring") or {}).get("then") if isinstance(c.get("daring"), dict) else None
        if isinstance(th, dict) and th.get("cut_on"): probes.append((c, "cut_on", th["cut_on"]))
        if isinstance(c.get("arrow"), dict) and c["arrow"].get("anchor"): probes.append((c, "arrow", c["arrow"]["anchor"]))
    seen_in = {}
    for c, field, a in probes:
        label = c["id"] if field == "anchor" else c["id"] + {"out": " (out)", "cut_on": " (cut)", "arrow": " (arrow)"}[field]
        n, _ = normalize_map(a)
        if not n:
            rows.append(("ERROR", label, f"{field} is empty once punctuation is removed")); continue
        at = occurrences(norm, n)
        if not at:
            words = n.split()
            hint = ""
            for take in (6, 5, 4):
                if len(words) > take:
                    part = " ".join(words[:take])
                    if occurrences(norm, part):
                        hint = f" — the first {take} words do match, so the rest of it drifts from what she said"
                        break
            rows.append(("ERROR", label, f"not in the transcript{hint}. Ctrl-F will find nothing"))
            continue
        if len(at) > 1:
            rows.append(("ERROR", label,
                         f"occurs {len(at)} times — Ctrl-F will land on the wrong one. Extend it with the words on either side"))
            continue
        p = at[0]
        exact = re.sub(r"\s+", " ", transcript[idx[p]: idx[p + len(n) - 1] + 1])
        if field == "anchor":
            positions.append((idx[p], c["id"]))
            seen_in[c["id"]] = idx[p]
        elif c["id"] in seen_in and idx[p] <= seen_in[c["id"]]:
            rows.append(("ERROR", label, {"out": "the release phrase comes before the phrase the punch starts on",
                                          "cut_on": "the cut to shot 2 comes before the phrase the clip starts on",
                                          "arrow": "the arrow arrives before the picture does"}[field]))
        if exact.strip() != a.strip():
            if field in ("anchor", "out"): fixes[(c["id"], field)] = exact.strip()
            rows.append(("FIX", label, f"she actually says: {exact.strip()!r} — use that verbatim"
                         + ("" if field in ("anchor", "out") else " (by hand: --fix leaves this one alone)")))
    # cue order should follow transcript order
    for (pa, ida), (pb, idb) in zip(positions, positions[1:]):
        if pb < pa:
            rows.append(("WARN", idb, f"appears earlier in the transcript than {ida} — the cue order is wrong"))
    return rows, fixes


def apply_fixes(path, fixes):
    """Rewrite anchors in the episode file to the transcript's exact wording."""
    src = open(path, encoding="utf-8").read()
    n = 0
    for (cid, field), exact in fixes.items():
        pat = re.compile(r'(id="' + re.escape(cid) + r'".*?' + field + r'=)("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', re.S)
        rep = '\\1' + repr(exact).replace("\\", "\\\\")
        src, k = pat.subn(rep, src, count=1)
        n += k
    open(path, "w", encoding="utf-8").write(src)
    return n


def report(ep, transcript):
    """Print every problem and an honest tally. Returns (failing labels, labels that only differ in wording, fixes)."""
    rows, fixes = check(ep, transcript)
    for lvl, cid, msg in rows:
        print(f"{lvl:5} {cid:26} {msg}")
    total = (sum(1 for c in ep.cues if c.get("anchor")) + sum(1 for c in ep.cues if c.get("out"))
             + sum(1 for c in ep.cues if isinstance(c.get("daring"), dict) and isinstance(c["daring"].get("then"), dict)
                   and c["daring"]["then"].get("cut_on"))
             + sum(1 for c in ep.cues if isinstance(c.get("arrow"), dict) and c["arrow"].get("anchor")))
    failing = {cid for lvl, cid, _ in rows if lvl == "ERROR"}
    wording = {cid for lvl, cid, _ in rows if lvl == "FIX"} - failing
    exact = total - len(failing) - len(wording)
    # A FIX is unique, but not in her exact words: Ctrl-F may still miss it on punctuation, so it is not counted as
    # verbatim (until 15 Oct 2026 it was, and the script exited 0 on it).
    print(f"\n{exact}/{total} phrases are exact and unique · {len(wording)} unique but worded differently from the "
          f"transcript · {len(failing)} failing")
    return failing, wording, fixes


if __name__ == "__main__":
    import hashlib, os
    from episode import load
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict, fix = "--strict" in sys.argv, "--fix" in sys.argv
    if len(args) != 2: sys.exit(__doc__)
    raw = open(args[1], encoding="utf-8").read()
    transcript = strip_markers(raw)
    # Say exactly which transcript this report is about — a sheet checked against an older export is not checked.
    print(f"{os.path.basename(args[0])} against {os.path.basename(args[1])} · {len(transcript.split()):,} words · "
          f"sha256 {hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}\n")
    ep = load(args[0])
    failing, wording, fixes = report(ep, transcript)
    if fix and fixes:
        print("\nrewrote", apply_fixes(args[0], fixes), "anchors in", args[0], "— checking again:\n")
        ep = load(args[0])
        failing, wording, fixes = report(ep, transcript)
    if strict and wording:
        print("--strict: a phrase worded differently from the transcript fails too. Run with --fix "
              "(the (cut) and (arrow) ones by hand), then run --strict again.")
    sys.exit(1 if failing or (strict and wording) else 0)
