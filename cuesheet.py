#!/usr/bin/env python3
"""Build the episode cue sheet — one page, two lives.

Before the transcript exists it is the SHOT PLAN: what to generate and retrieve,
keyed to script beats. After the transcript lands the same page becomes the CUE
SHEET: every cue keyed to a verbatim phrase to Ctrl-F in Descript.

    python3 cuesheet.py episodes/S2E4.py               → out/S2E4/cuesheet.html
    python3 cuesheet.py episodes/S2E4.py --plan-first → anchored cues, but Generate/Retrieve still
                                                        on top (both passes run in one go)
    python3 cuesheet.py episodes/S2E4.py --force      → build even with prompt-lint errors
"""
import argparse, hashlib, html, json, os, sys, urllib.parse
from episode import load
from lint_prompts import lint, worst, lint_daring_all, lint_daring_then_all
from style import (KINDS, OVERLAY_KINDS, CHIP_ORDER, CHIP_MERGE, MODES, STYLE_IMAGE, STYLE_VIDEO,
                   GUARDS, RIGHTS, PICTURE_POLICY, PIP, HERO_CLIP, STYLE_VIDEO_NOFRAME, SAYS_WHAT_IT_IS,
                   GUARD_LINES, CAPTION_RULE, REF_LEAD, REF_LEAD_DARING, REF_INTRO, STYLE_VIDEO_DARING, DARING)
try:
    from characters import CHARACTERS
except ImportError:
    CHARACTERS = {}


def esc(s): return html.escape(str(s if s is not None else ""))


# What a tick vouches for: the phrase it was placed on and the file that went there. If any of these change after it
# was ticked, the page shows the cue as changed and unticked, so it gets placed again. Notes, beats, timecodes and
# prompts can change freely without disturbing a tick.
FP_FIELDS = ("kind", "anchor", "out", "mode", "dur", "text", "ref", "hl", "rows", "between", "names", "name", "role",
             "hero", "sub", "sub2", "src", "steps", "who", "credit", "crop", "matte", "arrow", "file", "places",
             "context", "nodes")


def fingerprint(q):
    d = {k: q.get(k) for k in FP_FIELDS if q.get(k) not in (None, "", (), [])}
    th = (q.get("daring") or {}).get("then") if isinstance(q.get("daring"), dict) else None
    if isinstance(th, dict) and th.get("cut_on"): d["cut_on"] = th["cut_on"]
    return hashlib.sha1(json.dumps(d, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")).hexdigest()[:10]


def tc_short(t):
    if not t: return ""
    p = str(t).split(":")
    return f"{int(p[1])}:{p[2]}" if len(p) == 3 and p[0] == "00" else str(t)


def search_url(c):
    if c.get("link"): return c["link"]          # the exact page is known — go there, not to a search
    q = urllib.parse.quote_plus(c.get("search") or c["what"])
    if c["rights"] in ("pd", "cc"):
        return f"https://commons.wikimedia.org/w/index.php?search={q}&title=Special:MediaSearch&type=image"
    return f"https://www.google.com/search?tbm=isch&q={q}"


def group(ep):
    starts = {s[0]: s for s in ep.sections}
    groups, cur = [], None
    for q in ep.cues:
        if q["id"] in starts:
            cur = dict(title=starts[q["id"]][1], sub=starts[q["id"]][2], cues=[]); groups.append(cur)
        if cur is None:
            cur = dict(title="Cues", sub="", cues=[]); groups.append(cur)
        cur["cues"].append(q)
    return groups


def cue_row(q, n, lint_rows):
    kind = q["kind"]; label, hue, _ = KINDS[kind]
    chipkind = CHIP_MERGE.get(kind, kind)
    star = "★" in q["note"] or "★" in (q.get("why") or "")
    warn = "⚠" in q["note"]
    note = (q["note"] if kind != "punch" else q["why"]).replace("★ ", "").replace("⚠ ", "")
    warn_label = "correction" if "SPELL IT" in q["note"] else "watch this beat"
    cls = " ".join(filter(None, ["cue", f"k-{kind}", "is-star" if star else "", "is-warn" if warn else "",
                                 "needs-anchor" if not q["anchor"] else ""]))
    mode = "" if kind == "punch" else f'<span class="mode mode-{esc(q["mode"])}">{esc(q["mode"])}</span>'
    dur = f'<span class="dur">{esc(q["dur"])}</span>' if q["dur"] not in ("—", None) else ""
    asset = "" if kind == "punch" else f'<code class="asset">{esc(q["id"])}{"" if kind == "ai" else ""}</code>'
    if q["anchor"]:
        phrase = (f'<button class="anchor" data-copy="{esc(q["anchor"])}" title="Copy for Ctrl-F in Descript">'
                  f'<span class="q">&ldquo;</span>{esc(q["anchor"])}<span class="q">&rdquo;</span><span class="copyhint">copy</span></button>')
    else:
        phrase = f'<p class="beat"><span class="beatlabel">script beat</span>{esc(q["beat"])}</p>'
    extra = ""
    if kind == "picture":
        r = RIGHTS[q["rights"]]
        extra = (f'<p class="pic"><b>{esc(q["what"])}</b> · <span class="rights r-{esc(r[1])}">{esc(r[0])}</span>'
                 + (f' · credit <i>{esc(q["credit"])}</i>' if q.get("credit") else "") + "</p>")
    if kind == "ai" and lint_rows:
        items = "".join(f'<li class="l-{l.lower()}">{esc(m)}</li>' for l, m in lint_rows)
        extra += f'<ul class="lint">{items}</ul>'
    tcs = tc_short(q["tc"]) if q["tc"] else (q.get("approx") or "")
    return f'''
        <li class="{cls}" data-kind="{esc(chipkind)}" data-n="{n}" data-id="{esc(q['id'])}">
          <label class="tick"><input type="checkbox" data-n="{n}" data-id="{esc(q['id'])}" data-fp="{fingerprint(q)}" aria-label="Mark cue {n} done"><span></span></label>
          <span class="tc{' approx' if not q['tc'] else ''}">{esc(tcs)}</span>
          <div class="body">
            <div class="meta">
              <span class="chip" style="--hue:{hue}">{esc(label)}</span>
              {mode}{dur}{asset}
              {'<span class="flag flag-star">key moment</span>' if star else ''}
              {('<span class="flag flag-daring">' + ("daring take" if q.get("daring_only") else "+ daring take") + '</span>') if kind == "ai" and isinstance(q.get("daring"), dict) else ''}
              {'<span class="flag flag-warn">'+warn_label+'</span>' if warn else ''}
              {'' if q["anchor"] else '<span class="flag flag-pend">anchor when the transcript lands</span>'}
            </div>
            {phrase}
            {extra}
            {'<p class="note">'+esc(note)+'</p>' if note else ''}
          </div>
        </li>'''


def ref_lead(refs, template):
    """One sentence per person: who the person in the attached reference(s) is, and what to keep from them.
    With two people attached (S2E9: Saul and Samuel), "the man in the reference images" fits either of them, so each
    sentence names him by what tells them apart — the reference's `tag` ("very tall man in the deep purple robe")."""
    people = {}
    for r in refs:
        people.setdefault((r["name"], r["who"], r.get("poss", "his"), r.get("tag")), []).append(r)
    several = len(people) > 1
    out = []
    for (name, who, poss, tag), rs in people.items():
        many = len(rs) > 1
        out.append(template.format(who=tag if (several and tag) else who, name=name, poss=poss,
                                   img="images" if many else "image",
                                   them="those images" if many else "that image", its="their" if many else "its",
                                   pose="poses" if many else "pose"))
    return " ".join([REF_INTRO[2 if len(refs) > 1 else 1]] + out) if out else ""


def without_images(refs):
    """The line for a clip made without its reference images, when the prompts only NAME the people (S2E9 on,
    EPISODE people_in_prompts="named"): the lead sentences go, and each person's description from his card goes in
    their place."""
    people = []
    for r in refs:
        if r["name"] not in people: people.append(r["name"])
    if not people: return ""
    n = 1 + len(people)                               # REF_INTRO, then one lead sentence per person
    nth = {2: "two", 3: "three", 4: "four"}.get(n, str(n))
    whose = (f"{people[0]}'s description from his card" if len(people) == 1 else
             ", ".join(f"{p}'s" for p in people[:-1]) + f" and {people[-1]}'s descriptions from their cards")
    return (f"Without the images, delete the first {nth} sentences and paste {whose} in their place — with the images "
            f"attached the prompt only names {'him' if len(people) == 1 else 'them'}.")


def lint_list(rows):
    if not rows: return ""
    return '<ul class="lint">' + "".join(f'<li class="l-{l.lower()}">{esc(m)}</li>' for l, m in rows) + "</ul>"


def prompt_card(p, lint_rows, refs=(), drefs=(), dlint=(), trefs=(), tlint=(), named=False):
    t2v = p["frames"] == "none"
    daring = p.get("daring") if isinstance(p.get("daring"), dict) else None
    then = daring.get("then") if daring and isinstance(daring.get("then"), dict) else None
    # A daring-only clip (S2E9) has no safe take: the card is the daring take alone, saved under the clip's own name.
    only = bool(daring) and bool(p.get("daring_only"))
    clip_file = f"ai/{p['id']}.mp4" if only else f"ai/{p['id']}-daring.mp4"
    clip_file_2 = f"ai/{p['id']}-2.mp4" if only else f"ai/{p['id']}-daring-2.mp4"
    frames = ("Text to video — no input image. The scene and the action go in as one prompt."
              if t2v else "Start frame only." if p["frames"] == "start"
              else "★ Start AND end frame. End = " + p["end_image"])
    lead = ref_lead(refs, REF_LEAD) if (t2v and refs) else ""
    if lead:
        files = " and ".join(r["file"] for r in refs)
        frames = (f"Text to video with a reference image: attach {files}. In Flow choose Ingredients, not Frames — "
                  f"a reference fixes what he looks like and leaves the shot to the words, where a start frame would fix the "
                  f"whole picture. In the Gemini app, attach it to the prompt. "
                  + (without_images(refs) if named else
                     "No reference? Paste the prompt and delete its first two sentences; the rest describes him in the "
                     "same words as every other clip of him."))
    where = (f'Runs on: <button class="anchor inline" data-copy="{esc(p["anchor"])}">&ldquo;{esc(p["anchor"])}&rdquo;<span class="copyhint">copy</span></button>'
             if p["anchor"] else f'Runs on: <i>{esc(p["beat"])}</i>')
    if only:
        two_boxes = ""
    elif t2v:
        guards = " ".join(GUARD_LINES.get(g, g) for g in p.get("guards", ()))
        whole = " ".join(x for x in (lead, p["image"], p["video"], guards, STYLE_VIDEO_NOFRAME) if x)
        label = "reference + text to video · Flow Ingredients or Gemini" if lead else "Flow · Veo · text to video"
        title = "Safe take · face hidden" if daring else "One prompt"
        shown_lead = f'<i class="reflead">{esc(lead)}</i> ' if lead else ""
        two_boxes = f'''<div class="pbox t2v{' withref' if lead else ''}">
            <div class="plabel">{title} <span>{esc(label)}</span></div>
            <button class="ptext" data-copy="{esc(whole)}">{shown_lead}{esc(p["image"])} <b>{esc(p["video"])}</b><span class="stylenote">+ {"the guards for this shot and " if p.get("guards") else ""}the silent/one-take block</span><span class="copyhint">copy</span></button>
            <p class="frames">{esc(frames)}{(" Save as ai/" + esc(p["id"]) + ".mp4.") if daring else ""}</p>
          </div>'''
    else:
        two_boxes = f'''<div class="two">
          <div class="pbox">
            <div class="plabel">1 · Image prompt <span>ChatGPT</span></div>
            <button class="ptext" data-copy="{esc(p["image"] + " " + STYLE_IMAGE)}">{esc(p["image"])}<span class="stylenote">+ style block</span><span class="copyhint">copy</span></button>
          </div>
          <div class="pbox">
            <div class="plabel">2 · Video prompt <span>Flow · Veo</span></div>
            <button class="ptext" data-copy="{esc(p["video"] + " " + STYLE_VIDEO)}">{esc(p["video"])}<span class="stylenote">+ guard rail</span><span class="copyhint">copy</span></button>
            <p class="frames">{esc(frames)}</p>
          </div>
        </div>'''
    daring_box = ""
    if daring:
        dlead = ref_lead(drefs, REF_LEAD_DARING) if drefs else ""
        dguards = " ".join(GUARD_LINES.get(g, g) for g in daring.get("guards", ()))
        dwhole = " ".join(x for x in (dlead, daring["image"], daring["video"], dguards, STYLE_VIDEO_DARING) if x)
        dfiles = (" and ".join(r["file"] for r in drefs) if len(drefs) < 3 else
                  ", ".join(r["file"] for r in drefs[:-1]) + " and " + drefs[-1]["file"])
        dlabel = (("references + text to video · Gemini app" if len(drefs) > 3 else
                   "references + text to video · Flow Ingredients or Gemini") if dlead else "Flow · Veo · text to video")
        # Flow's Ingredients takes three images, the Gemini app five: a card that attaches four goes to the Gemini app.
        dwhere = ("attachments in the Gemini app, since Flow's Ingredients takes only three. " if len(drefs) > 3
                  else "Ingredients in Flow, attachments in the Gemini app. ")
        dattach = f"Attach {dfiles} — {dwhere}" if dfiles else "No reference — he is not in this shot. "
        if then:
            dframes = (dattach
                       + f"Save as {clip_file}. It is the first of two shots: it goes on the phrase, and the "
                       f"edit cuts to shot 2 on “{then['cut_on']}”. Start a new Gemini chat for each shot, and take three "
                       f"or four outputs — this one fails more often.")
        elif only:
            dframes = (dattach
                       + f"Save as {clip_file}. It is the only take of this beat, so make three or four outputs and keep "
                       f"the one that holds together.")
        else:
            dframes = (dattach
                       + f"Save as {clip_file}, beside the safe take; it goes on the same phrase, and you keep "
                       f"whichever of the two holds together. Take three or four outputs — this one fails more often.")
        if named and drefs:
            dframes += " " + without_images(drefs)
        daring_box = f'''<div class="pbox t2v daring">
            <div class="plabel">Daring take{" · shot 1 of 2" if then else ""} · {esc(daring.get("dur", "8s"))} <span>{esc(dlabel)}</span></div>
            <button class="ptext" data-copy="{esc(dwhole)}">{f'<i class="reflead">{esc(dlead)}</i> ' if dlead else ''}{esc(daring["image"])} <b>{esc(daring["video"])}</b><span class="stylenote">+ {"the guards for this shot and " if daring.get("guards") else ""}the silent/one-take block, without the camera limit</span><span class="copyhint">copy</span></button>
            <p class="frames">{esc(dframes)}</p>
            {lint_list(dlint)}
            {'<p class="note">' + esc(daring["note"]) + '</p>' if daring.get("note") else ''}
          </div>'''
        if then:
            # A second shot the edit cuts to (added for S2E7): the dangerous moment happens in the cut between the two,
            # which is the only way the Gemini app will make a man thrown overboard with his face on screen.
            tlead = ref_lead(trefs, REF_LEAD_DARING) if trefs else ""
            tguards = " ".join(GUARD_LINES.get(g, g) for g in then.get("guards", ()))
            twhole = " ".join(x for x in (tlead, then["image"], then["video"], tguards, STYLE_VIDEO_DARING) if x)
            # Four images go to the Gemini app, since Flow's Ingredients takes three (S2E9's séance, shot 2).
            tfiles = (" and ".join(r["file"] for r in trefs) if len(trefs) <= 3 else
                      ", ".join(r["file"] for r in trefs[:-1]) + " and " + trefs[-1]["file"])
            tlabel = (("references + text to video · Gemini app" if len(trefs) > 3 else
                       "references + text to video · Flow Ingredients or Gemini") if tlead else "Flow · Veo · text to video, or Gemini")
            twhere = ("attachments in the Gemini app, since Flow's Ingredients takes only three. " if len(trefs) > 3
                      else "Ingredients in Flow, attachments in the Gemini app. ")
            tframes = ((f"Attach {tfiles} — {twhere}" if tfiles else "No reference — he is not in this shot. ")
                       + f"Save as {clip_file_2} and cut to it on “{then['cut_on']}”, straight from shot 1 — "
                       f"no dissolve. Trim the two together to the length of the phrase."
                       + ((" " + without_images(trefs)) if named and trefs else ""))
            daring_box += f'''<div class="pbox t2v daring">
            <div class="plabel">Daring take · shot 2 of 2 · cut on “{esc(then["cut_on"])}” · {esc(then.get("dur", "8s"))} <span>{esc(tlabel)}</span></div>
            <button class="ptext" data-copy="{esc(twhole)}">{f'<i class="reflead">{esc(tlead)}</i> ' if tlead else ''}{esc(then["image"])} <b>{esc(then["video"])}</b><span class="stylenote">+ {"the guards for this shot and " if then.get("guards") else ""}the silent/one-take block, without the camera limit</span><span class="copyhint">copy</span></button>
            <p class="frames">{esc(tframes)}</p>
            {lint_list(tlint)}
            {'<p class="note">' + esc(then["note"]) + '</p>' if then.get("note") else ''}
          </div>'''
    return f'''
      <article class="prompt" id="{esc(p["id"])}">
        <header>
          <span class="tc">{esc(tc_short(p["tc"]) if p["tc"] else (p.get("approx") or ""))}</span>
          <h3>{esc(p["title"])}</h3>
          <span class="dur">{esc(p["dur"])}</span>
          <span class="prio">priority {esc(p["priority"])}</span>
          {'<span class="flag flag-hero">hero clip</span>' if p.get("hero_clip") else ''}
          {"".join(f'<span class="flag flag-ref">attach {esc(r["file"])}</span>' for r in (refs if lead else (list(drefs) + [r for r in trefs if r not in drefs]) if only else ()))}
          {('<span class="flag flag-daring">' + ('daring take' if only else '+ daring take') + (' · 2 shots' if then else '') + '</span>') if daring else ''}
          <code class="asset">ai/{esc(p["id"])}.mp4</code>
        </header>
        <p class="on">{where}</p>
        {two_boxes}
        {lint_list(lint_rows)}
        {'<p class="note">'+esc(p["note"].replace("★ ",""))+'</p>' if p["note"] else ''}
        {daring_box}
      </article>'''


def character_card(key, attached, ai, with_daring, named=False):
    """One card per standing character in the episode (added for S2E9), however many of his views it attaches: which
    file goes on which clip, and either his description (made) or the two ChatGPT prompts that make him. With the prompts
    only naming him (named=True) the description is the fallback for a clip made without the images, and says so."""
    ch = CHARACTERS.get(key, {})
    name = ch.get("name") or attached[0]["name"]
    folder = ch.get("folder") or attached[0].get("folder", "")

    def links(ps):
        return ", ".join(f'<a href="#{esc(p["id"])}">{esc(p["title"])}</a>' for p in ps) or "<i>no clip yet</i>"

    def users(rid):
        out = [p for p in ai if rid in p.get("refs", ())]
        for p in with_daring:
            d = p["daring"]
            th = d["then"] if isinstance(d.get("then"), dict) else {}
            if (rid in d.get("refs", ()) or rid in th.get("refs", ())) and p not in out:
                out.append(p)
        return out

    rows = "".join(f'<li><code>{esc(r["file"])}</code> — {esc(r["prompt"].split(";")[0])}: {links(users(r["id"]))}</li>'
                   for r in attached)
    attach_list = f'<p class="frames"><b>Attached in this episode</b></p><ul class="nots">{rows}</ul>'
    if ch.get("made"):
        status = '<span class="flag flag-made">standing character · made</span>'
        desc = ch.get("description") or ""
        label = ("Description <span>only for a clip made without his images</span>" if named
                 else "Description <span>put it in every prompt he is in</span>")
        use = (f' With his images attached, a prompt calls him {esc(name)} and says only what the scene changes; this '
               f'paragraph is for a clip made without them, pasted in place of the card&rsquo;s first sentences.'
               if named else "")
        body = (f'<div class="pbox t2v withref">'
                f'<div class="plabel">{label}</div>'
                f'<button class="ptext" data-copy="{esc(desc)}">{esc(desc)}<span class="copyhint">copy</span></button>'
                f'<p class="frames">Made once and used in every episode — attach the files from <code>{esc(folder)}</code> '
                f'in the FaithForReal folder. Never regenerate them for one episode: every clip of him on the channel comes '
                f'from the same set.{use}</p>{attach_list}</div>')
    else:
        d = ch.get("design") or {}
        names = ", ".join(r["file"] for r in ch.get("refs", ()))
        status = '<span class="flag flag-ref">character model · make this first</span>'
        body = (f'<div class="two">'
                f'<div class="pbox t2v withref"><div class="plabel">1 · The lineup <span>ChatGPT · four men in one image</span></div>'
                f'<button class="ptext" style="white-space:pre-line" data-copy="{esc(d.get("lineup", ""))}">{esc(d.get("lineup", ""))}'
                f'<span class="copyhint">copy</span></button></div>'
                f'<div class="pbox t2v withref"><div class="plabel">2 · His reference set <span>same chat · five images and a paragraph</span></div>'
                f'<button class="ptext" style="white-space:pre-line" data-copy="{esc(d.get("views", ""))}">{esc(d.get("views", ""))}'
                f'<span class="copyhint">copy</span></button></div>'
                f'</div>'
                f'<div class="pbox t2v withref"><p class="frames">Pick one, put his number in the second prompt, and stay '
                f'in the same chat for the five views. Save them once, for the whole channel, in '
                f'<code>FaithForReal\\{esc(folder)}\\</code> as {esc(names)}, with the paragraph ChatGPT writes at the end '
                f'beside them as <code>{esc(name)}_Character_Description.txt</code>. If his face drifts from one view to the '
                f'next, attach the lineup again with the request. '
                + ('The clip cards only name him — the images carry his look — so the paragraph is for a clip made '
                   'without them.' if named else
                   'Until that paragraph exists the clip cards describe him from what the lineup fixes — his age, his '
                   'height, his hair and every piece of the costume; once it does, it goes into every prompt he is in, '
                   'the way Jesus\'s does.')
                + f'</p>{attach_list}</div>')
    return (f'\n      <article class="prompt refcard" id="char-{esc(key)}">'
            f'\n        <header>\n          <h3>{esc(name)}</h3>\n          {status}\n'
            f'          <code class="asset">{esc(folder)}\\</code>\n        </header>\n        {body}\n      </article>')


def picture_card(c):
    r = RIGHTS[c["rights"]]
    full = c["mode"] == "full"
    strip = c["mode"] == "strip"
    a = c.get("arrow")
    arrow_rows = ""
    if a:
        aw = (f'<button class="anchor inline" data-copy="{esc(a["anchor"])}">&ldquo;{esc(a["anchor"])}&rdquo;<span class="copyhint">copy</span></button>'
              if a.get("anchor") else f'<i>{esc(a.get("beat") or "")}</i>')
        arrow_rows = (f'<dt>Arrow on</dt><dd>{aw}</dd>'
                      f'<dt>Target</dt><dd>x {a["at"][0]}, y {a["at"][1]} of the picture'
                      + (' — <b>provisional</b>, check it with <code class="asset">python3 arrowgrid.py '
                         + esc(c["id"]) + '</code> once the file is downloaded' if a.get("provisional") else '')
                      + '</dd>')
    where = (f'<button class="anchor inline" data-copy="{esc(c["anchor"])}">&ldquo;{esc(c["anchor"])}&rdquo;<span class="copyhint">copy</span></button>'
             if c["anchor"] else f'<i>{esc(c["beat"])}</i>')
    # A generated reconstruction (rights "gen") with prompt=… is made, not found (added for S2E7): the card gives the
    # prompt with the house image style appended, ready to copy, and no search link — there is nothing to search for.
    make_rows = ""
    if c.get("prompt"):
        whole = c["prompt"] + " " + STYLE_IMAGE
        make_rows = (f'<dt>Make it</dt><dd>{esc(c["source"])}'
                     f'<button class="ptext" data-copy="{esc(whole)}">{esc(c["prompt"])}<span class="stylenote">+ the house image style</span>'
                     f'<span class="copyhint">copy</span></button></dd>')
    # Already downloaded and framed (retrieved=dict(…), added for S2E9): say where it came from, not how to find it.
    got = c.get("retrieved") if isinstance(c.get("retrieved"), dict) else None
    if got:
        find_row = ('<dt>Got it</dt><dd>' + esc(c["source"]) + ' — <a href="' + esc(search_url(c))
                    + '" target="_blank" rel="noopener">file page &rarr;</a></dd>')
        save_row = (f'<dt>Saved as</dt><dd><code class="asset">pictures/raw/{esc(got.get("file") or c["id"])}</code> — '
                    f'{esc(got.get("size") or "")}{", " if got.get("size") else ""}downloaded {esc(got.get("on") or "")}, '
                    f'and framed into the pack: nothing to fetch.'
                    + (f' <b>For the video description:</b> {esc(got["owe"])}' if got.get("owe") else '') + '</dd>')
    else:
        save_row = (f'<dt>Save as</dt><dd><code class="asset">pictures/raw/{esc(c["id"])}.jpg</code> (or .png) — '
                    f'{esc(c.get("aspect") or "any shape")}. <b>Do not crop it.</b> '
                    + ("It is fitted to the whole frame on a dark ground, so the shape can be anything" if full else
                       "It is stretched to the width of the frame, so it wants to be at least four times as wide as it is tall"
                       if strip else
                       "The frame scales every picture to the same visual weight and centres it in the same band, so the "
                       "shape can be anything")
                    + "; " + ("keep the largest size the generator gives" if c.get("prompt") else
                              "just take the largest version you can find"
                              + (" — the biggest scan on the file page, because this one goes full screen" if full else ""))
                    + '</dd>')
    return f'''
      <article class="piccard" id="{esc(c["id"])}">
        <header>
          <span class="tc">{esc(tc_short(c["tc"]) if c["tc"] else (c.get("approx") or ""))}</span>
          <h3>{esc(c["what"])}</h3>
          <span class="rights r-{esc(r[1])}">{esc(r[0])}</span>
        </header>
        <dl>
          <dt>Runs on</dt><dd>{where}</dd>{arrow_rows}
          {find_row if got else make_rows if c.get("prompt") else ('<dt>Take it</dt><dd>' + esc(c["source"]) + '</dd>') if c["rights"] == "own" else ('<dt>Find it</dt><dd>' + esc(c["source"]) + ' — <a href="' + esc(search_url(c)) + '" target="_blank" rel="noopener">' + ('open' if c.get("link") else 'search') + ' &rarr;</a></dd>')}
          <dt>Renders as</dt><dd>{('<code class="asset">overlays/' + esc(c["id"]) + '-1.png</code> then <code class="asset">' + esc(c["id"]) + '-2.png</code> — the picture, then the picture with the arrow. Two scenes, cross-fade six frames between them, exactly like kinetic text.') if a else ('<code class="asset">overlays/' + esc(c["id"]) + '.png</code>' + (' — a full 1920&times;1080 frame that replaces her, cut in and out like a clip.' if full else ' — laid across the bottom of the frame, over her, with her face still in shot above it. Fade it in and out like a picture in the corner.' if strip else ' — framed into the corner over her shoulder.'))}</dd>
          {save_row}
          <dt>Credit line</dt><dd>{esc(c["credit"]) if c.get("credit") else "<i>none</i>"}</dd>
        </dl>
        {'<p class="note">'+esc(c["note"])+'</p>' if c["note"] else ''}
      </article>'''


def build(ep, report, plan_first=None):
    m = ep.meta; state = ep.state; n = ep.counts()
    if plan_first is None: plan_first = (state == "plan")
    named = m.get("people_in_prompts") == "named"            # S2E9 on: prompts name the people; the images carry them
    groups = group(ep)
    counts = {}
    for q in ep.cues:
        k = CHIP_MERGE.get(q["kind"], q["kind"]); counts[k] = counts.get(k, 0) + 1
    chips = "".join(f'<button class="filt" data-kind="{k}" style="--hue:{KINDS[k][1]}"><i></i>{KINDS[k][0]}<b>{counts[k]}</b></button>'
                    for k in CHIP_ORDER if counts.get(k))

    rows, i = [], 0
    for g in groups:
        rows.append(f'<section class="grp"><div class="grp-head"><h2>{esc(g["title"])}</h2><p>{esc(g["sub"])}</p></div><ol class="cues">')
        for q in g["cues"]:
            i += 1; rows.append(cue_row(q, i, report.get(q["id"]) if q["kind"] == "ai" else None))
        rows.append("</ol></section>")

    ai = sorted(ep.by_kind("ai"), key=lambda c: c.get("priority", 9))
    dreport = lint_daring_all(ep)
    treport = lint_daring_then_all(ep)
    def resolve(ids): return [ep.reference(r) for r in ids if ep.reference(r)]
    def then_of(p):
        d = p.get("daring")
        return d["then"] if isinstance(d, dict) and isinstance(d.get("then"), dict) else {}
    prompts = "".join(prompt_card(p, report.get(p["id"], []), resolve(p.get("refs", ())),
                                  resolve((p.get("daring") or {}).get("refs", ())) if isinstance(p.get("daring"), dict) else [],
                                  dreport.get(p["id"], []),
                                  resolve(then_of(p).get("refs", ())), treport.get(p["id"], []), named=named)
                      for p in ai)
    with_daring = [p for p in ai if isinstance(p.get("daring"), dict)]
    refs_block = ""
    only_all = bool(ai) and all(p.get("daring_only") for p in ai)      # S2E9: daring takes only
    seen_chars = []
    if ep.references:
        cards = []
        for r in ep.references:
            if r.get("standing"):
                # A standing character gets ONE card, whichever of his views this episode attaches (S2E9).
                key = r.get("character")
                if key not in seen_chars:
                    seen_chars.append(key)
                    cards.append(character_card(key, [x for x in ep.references if x.get("character") == key],
                                                ai, with_daring, named=named))
                continue
            safe_users = [p for p in ai if r["id"] in p.get("refs", ())]
            daring_users = [p for p in with_daring if r["id"] in p["daring"].get("refs", ())]
            def links(ps): return ", ".join(f'<a href="#{esc(p["id"])}">{esc(p["title"])}</a>' for p in ps)
            used_on = "; ".join(x for x in (
                ("safe takes: " + links(safe_users)) if safe_users else "",
                ("daring takes: " + links(daring_users)) if daring_users else "") if x) or "<i>no clip yet</i>"
            if r.get("made"):
                status = '<span class="flag flag-made">made</span>'
                plabel = "Image prompt <span>already made — kept here to remake it</span>"
                advice = (f"Already made — keep it in the episode folder as <code>{esc(r['file'])}</code>. Attached to {used_on}. "
                          f"Once a clip has been made with it, do not swap it for another — every clip of him should come "
                          f"from the same file.")
            else:
                status = '<span class="flag flag-ref">make this first</span>'
                plabel = "Image prompt <span>ChatGPT or Gemini · make 3–4, keep one</span>"
                advice = (f"Attached to {used_on}. Keep the one where the cloth, the colours and the build are clearest"
                          + ("" if daring_users and not safe_users else " and the face is properly hidden; reject any "
                             "that turn his head toward the camera")
                          + ". Once a clip has been made with it, do not swap it for another — every clip of him should "
                            "come from the same file.")
            cards.append(f'''
      <article class="prompt refcard" id="ref-{esc(r["id"])}">
        <header>
          <h3>{esc(r["title"])}</h3>
          {status}
          <code class="asset">{esc(r["file"])}</code>
        </header>
        <div class="pbox t2v withref">
          <div class="plabel">{plabel}</div>
          <button class="ptext" data-copy="{esc(r["prompt"])}">{esc(r["prompt"])}<span class="copyhint">copy</span></button>
          <p class="frames">{advice}</p>
        </div>
        {'<p class="note">' + esc(r["note"]) + '</p>' if r.get("note") else ''}
      </article>''')
        many = len(ep.references) > 1
        names = [CHARACTERS.get(k, {}).get("name", k) for k in seen_chars]
        to_make = [CHARACTERS[k]["name"] for k in seen_chars if k in CHARACTERS and not CHARACTERS[k].get("made")]
    if ep.references and only_all and seen_chars:
        # Daring takes only (S2E9): every clip shows faces, so every clip attaches the front views — and the people are
        # standing characters, made once for the channel, so the intro is about character models rather than one
        # episode's reference image.
        who = ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]
        make_line = ((" " + " and ".join(to_make) + (" are" if len(to_make) > 1 else " is")
                      + " not made yet: the two prompts on " + ("their cards" if len(to_make) > 1 else "his card")
                      + " come before any clip.") if to_make else "")
        named_line = (" After that the prompt calls each man by name and says only what the scene changes — a borrowed "
                      "cloak, a torn hem — because the images already carry his face and his clothes. His full "
                      "description is on his card, for a clip made without the images." if named else "")
        refs_block = f'''
  <div class="stylebox refbox">
    <h3>The people who come back — {esc(who)}</h3>
    <p>When the same man is in more than one clip, text alone invents a slightly different man every time — another face,
    another beard, another robe. So each of them has a <b>character model</b>: five reference images, made once for the
    whole channel and attached to every clip he is in. A reference is <b>not a start frame</b>: in Flow it goes in through
    <b>Ingredients</b>, not Frames, and in the Gemini app you simply attach it. It fixes what he looks like and leaves the
    shot to the words.</p>
    <p>Every clip on this episode is a daring take, so every card attaches the <b>front view with the view from behind</b> —
    the front fixes the face, the back the cloth from every side — and the head-and-shoulders view where his face is the
    shot. Each card starts with one sentence saying who is who and what to keep; with two men in one shot it names each by
    what he is wearing.{named_line}{esc(make_line)} One note on length: the Gemini app generates with Gemini Omni, which hands back
    ten seconds where Veo hands back eight — same trim either way.</p>
  </div>
  {"".join(cards)}'''
    elif ep.references:
        refs_block = f'''
  <div class="stylebox refbox">
    <h3>{"The character references — him from behind, and him from the front" if many else "The character reference — one image of him, before any clip"}</h3>
    <p>He is in several clips, and text alone invents a slightly different man every time — another colour of cloak,
    another beard, another build. So he gets {"<b>reference images</b>" if many else "<b>one reference image</b>"}, attached to the clips where he is big enough to
    recognise. A reference is <b>not a start frame</b>: in Flow it goes in through <b>Ingredients</b>, not Frames, and in
    the Gemini app you simply attach it. A start frame fixes the whole first picture — composition, light, everything — which
    is where the driverless cart came from; a reference fixes only what he looks like and leaves the shot to the words.</p>
    <p>The <b>safe takes</b> get the costume reference only — full length, from behind, face turned away — because they never show his
    face, and a reference with a face invites the model to turn him round and show it.{" The <b>daring takes</b> get both: the front view fixes his face, the back view fixes the cloth from every side." if many else ""}
    Each card that uses a reference starts with one sentence saying who he is and what to keep; {"after it the prompt only names him, so if you ever run the card without the image, delete that sentence and paste the description from his card in its place." if named else "delete that sentence if you"
    + chr(10) + "    ever run the card without it."}{" A card marked <b>standing character</b> is someone the channel keeps — his images were made once, live in their own folder in FaithForReal, and every episode attaches the same files." if any(x.get("standing") for x in ep.references) else ""} One note on length: the Gemini app now generates with Gemini Omni, which hands back ten
    seconds where Veo hands back eight — same trim either way.</p>
  </div>
  {"".join(cards)}'''
    daring_box = ""
    if with_daring and only_all:
        daring_box = f'''
  <div class="stylebox daringbox">
    <h3>Daring takes only — no safe takes on this episode</h3>
    <p>Every card below is one <b>daring take</b>: the beat shot the way a film would shoot it — faces and what is on them,
    the camera moving, hands at work, several things happening at once. There is no safe take behind it to fall back on,
    so take three or four outputs per card rather than two, keep the one that holds together, and save it under the
    card's own name, <code>ai/&lt;id&gt;.mp4</code>; a take in two shots adds <code>ai/&lt;id&gt;-2.mp4</code>, cut to on
    the word the card names.</p>
    <div class="two">
      <div class="pbox"><div class="plabel">Lifted on every clip here</div><ul class="nots">{"".join(f"<li>{esc(x)}</li>" for x in DARING["lifted"])}</ul></div>
      <div class="pbox"><div class="plabel">Still held</div><ul class="nots">{"".join(f"<li>{esc(x)}</li>" for x in DARING["held"])}</ul></div>
    </div>
    {('<div class="pbox refused"><div class="plabel">Refused by the generator, whatever the house allows</div><ul class="nots">'
      + "".join(f"<li>{esc(x)}</li>" for x in DARING["refused"]) + '</ul></div>') if DARING.get("refused") else ''}
    <p class="fine">{esc(DARING["note"])}</p>
    <button class="ptext" data-copy="{esc(STYLE_VIDEO_DARING)}">{esc(STYLE_VIDEO_DARING)}<span class="copyhint">copy</span></button>
  </div>'''
    elif with_daring:
        daring_box = f'''
  <div class="stylebox daringbox">
    <h3>Two takes per clip — the safe one, and a daring one</h3>
    <p>Every card below has the <b>safe take</b> the house rules were written for — face hidden, camera still, one motion —
    and under it a <b>daring take</b> of the same beat, shot the way a film would shoot it. Make the safe one first, then
    try the daring one, and keep whichever holds together; both are cut to the same phrase, so either drops into the same
    place. Daring takes are saved as <code>ai/&lt;id&gt;-daring.mp4</code>; a daring take in two shots adds <code>ai/&lt;id&gt;-daring-2.mp4</code>, cut to on the word the card names.</p>
    <div class="two">
      <div class="pbox"><div class="plabel">Lifted on the daring takes</div><ul class="nots">{"".join(f"<li>{esc(x)}</li>" for x in DARING["lifted"])}</ul></div>
      <div class="pbox"><div class="plabel">Still held</div><ul class="nots">{"".join(f"<li>{esc(x)}</li>" for x in DARING["held"])}</ul></div>
    </div>
    {('<div class="pbox refused"><div class="plabel">Refused by the generator, whatever the house allows</div><ul class="nots">'
      + "".join(f"<li>{esc(x)}</li>" for x in DARING["refused"]) + '</ul></div>') if DARING.get("refused") else ''}
    <p class="fine">{esc(DARING["note"])}</p>
    <button class="ptext" data-copy="{esc(STYLE_VIDEO_DARING)}">{esc(STYLE_VIDEO_DARING)}<span class="copyhint">copy</span></button>
  </div>'''
    pics = "".join(picture_card(c) for c in ep.by_kind("picture"))
    nots = "".join(f"<li><b>{esc(w)}</b> — {esc(y)}</li>" for w, y in ep.not_pictured)
    punches = ep.by_kind("punch")
    punch_rows = "".join(
        f'<li><span class="tc">{esc(tc_short(p["tc"]) if p["tc"] else (p.get("approx") or ""))}</span>'
        + (f'<span class="inout">tighten on</span><button class="anchor inline" data-copy="{esc(p["anchor"])}">&ldquo;{esc(p["anchor"])}&rdquo;<span class="copyhint">copy</span></button>' if p["anchor"] else f'<i>{esc(p["beat"])}</i>')
        + (f'<span class="rel"><span class="inout">release on</span><button class="anchor inline" data-copy="{esc(p["out"])}">&ldquo;{esc(p["out"])}&rdquo;<span class="copyhint">copy</span></button></span>' if p.get("out") else "")
        + f'<span class="why">{esc(p["why"].replace("★ ", ""))}</span></li>' for p in punches)
    guards = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in GUARDS)
    hero = next((c for c in ai if c.get("hero_clip")), None)
    hero_box = f'''
    <div class="herobox">
      <h4>One clip an episode gets to break some of that — the hero clip</h4>
      <p>The table above is calibrated to what video models reliably fail at, and models improve. So one clip per
      episode is the <b>hero</b>: the shot worth spending real money and real iteration time on, where the guards that
      exist because the <i>model</i> could not do the thing are lifted. The guards that exist because of what the
      <i>channel</i> will not show are not lifted, ever.
      {"This episode's hero is <b>" + esc(hero["title"]) + "</b> — the card below is marked." if hero else "No hero clip is designated on this episode."}</p>
      <div class="two">
        <div class="pbox"><div class="plabel">Lifted on the hero</div><ul class="nots">{"".join(f"<li>{esc(x)}</li>" for x in HERO_CLIP["lifted"])}</ul></div>
        <div class="pbox"><div class="plabel">Held, always</div><ul class="nots">{"".join(f"<li>{esc(x)}</li>" for x in HERO_CLIP["held"])}</ul></div>
      </div>
      <p class="fine">{esc(HERO_CLIP["note"])}</p>
    </div>'''
    corr = "".join(f"<li><b>{esc(c[1])}</b> — she says &ldquo;{esc(c[0])}&rdquo;. {esc(c[2])}</li>" for c in ep.corrections)
    notes = "".join(f'<div class="call"><h3>{esc(t)}</h3><p>{esc(x)}</p></div>' for t, x in ep.notes)
    policy_yes = "".join(f"<li>{esc(x)}</li>" for x in PICTURE_POLICY["yes"])
    policy_no = "".join(f"<li>{esc(x)}</li>" for x in PICTURE_POLICY["no"])
    policy_sens = ""
    if m.get("sensitive"):
        items = "".join(f"<li>{esc(x)}</li>" for x in PICTURE_POLICY["sensitive"])
        policy_sens = (f'<div class="call sens"><h3>This episode has real people who were harmed in it</h3>'
                       f'<p>{esc(m["sensitive"])} On top of the standing rules, nothing from this list goes on screen:</p>'
                       f'<ul class="nots">{items}</ul></div>')
    lint_level = worst(report)

    overlays_n = sum(n.get(k, 0) for k in OVERLAY_KINDS)
    pending = sum(1 for q in ep.cues if not q["anchor"])
    # What the eyebrow counts. Daring takes only (S2E9) are the clips, not an extra; and a standing character is counted
    # as one model to make, not as the five images of him.
    n_daring = sum(1 for c in ep.by_kind("ai") if isinstance(c.get("daring"), dict))
    if only_all:
        clips_txt = f'{n.get("ai",0)} daring takes to generate'
    else:
        clips_txt = f'{n.get("ai",0)} clips to generate' + (f" (+ {n_daring} daring takes)" if n_daring else "")
    chars_to_make = [CHARACTERS[k]["name"] for k in seen_chars if k in CHARACTERS and not CHARACTERS[k].get("made")]
    episode_refs = [r for r in ep.references if not r.get("standing")]
    if seen_chars:
        refs_txt = ((f" + {len(chars_to_make)} character model" + ("s" if len(chars_to_make) > 1 else "") + " to make")
                    if chars_to_make else "")
        refs_txt += ((" + " + str(len(episode_refs)) + " reference image" + ("s" if len(episode_refs) > 1 else ""))
                     if episode_refs else "")
    else:
        refs_txt = ((" + " + str(len(ep.references)) + " reference image" + ("s" if len(ep.references) > 1 else ""))
                    if ep.references else "")
    pictures = ep.by_kind("picture")
    got_n = sum(1 for c in pictures if c.get("retrieved"))
    # "3 pictures to find" until any are in; then what is left to find, and what is already framed (S2E9).
    pics_txt = (f'{n.get("picture",0)} pictures to find' if not got_n else
                f'{got_n} pictures framed' if got_n == len(pictures) else
                f'{len(pictures) - got_n} pictures to find (+ {got_n} framed)')
    if state == "plan":
        eyebrow = f'Faith for Real · {esc(m["code"])} <span>shot plan · from the script</span> {clips_txt}{refs_txt} · {pics_txt} · {overlays_n} overlays coming'
        lede = ('This is the <strong>shot plan</strong>, built from the script before the shoot. The first two sections are the work to do now: '
                'generate the clips and find the pictures. Every cue is keyed to a <strong>script beat</strong>; when the transcript lands '
                'the beats become verbatim phrases, the overlays get rendered, and this page becomes the cue sheet.')
    elif plan_first:
        eyebrow = f'Faith for Real · {esc(m["code"])} <span>{esc(m.get("runtime") or "")} · make first, then place</span> {clips_txt}{refs_txt} · {pics_txt} · {len(ep.cues)} cues'
        if pictures and got_n == len(pictures):
            lede = ('Both passes at once: the phrases are already anchored to the transcript, the overlays are rendered and '
                    'the pictures are framed, but the <strong>clips still have to be made</strong> — so that section comes '
                    'first. Everything below it is ready to place now.')
        else:
            lede = ('Both passes at once: the phrases are already anchored to the transcript and the overlays are rendered, '
                    'but the <strong>clips and pictures still have to be made</strong> — so those two sections come first. Do them, say the word, '
                    'and they get framed into the pack. Everything below that is ready to place now.')
    else:
        eyebrow = f'Faith for Real · {esc(m["code"])} <span>{esc(m.get("runtime") or "")}</span> {len(ep.cues)} cues' + (f' · {pending} still need an anchor' if pending else '')
        lede = ('Every cue is anchored to a <strong>verbatim phrase</strong> from the Descript transcript, not a timecode. '
                'Click any phrase to copy it, then Ctrl-F it in Descript\'s script view and drop the asset on the words. '
                'Timecodes are for orientation only — they drift the moment you trim, the phrases don\'t.')
    if m.get("lede"): lede += " " + esc(m["lede"])

    folder = esc(m["assets_folder"])
    conv = f'''
  <div class="conv">
    <div><h4>Band</h4><p>{esc(MODES["band"])}</p></div>
    <div><h4>Dim</h4><p>{esc(MODES["dim"])}</p></div>
    <div><h4>Cut</h4><p>{esc(MODES["cut"])}</p></div>
    <div><h4>Picture</h4><p>{esc(MODES["pip"])}</p></div>
    {('<div><h4>Picture across the bottom</h4><p>' + esc(MODES["strip"]) + '</p></div>') if any(c.get("mode") == "strip" for c in ep.by_kind("picture")) else ''}
    <div><h4>Map</h4><p>{esc(MODES["map"])}</p></div>
    <div><h4>Chart</h4><p>{esc(MODES["chart"])}</p></div>
    <div><h4>Clip in the corner</h4><p>{esc(MODES["pipclip"])}</p></div>
    <div><h4>Punch-in</h4><p>{esc(MODES["punch"])}</p></div>
    <div><h4>Where the files are</h4><p><code>{folder}</code> — <code>overlays\\</code> for everything you drop on her, <code>ai\\</code> for the clips you generate, <code>pictures\\raw\\</code> for what you download.</p></div>
  </div>'''

    lint_banner = ""
    if lint_level == 3:
        lint_banner = '<div class="call err"><h3>Prompt lint found errors</h3><p>Fix the red items on the prompt cards before generating anything.</p></div>'
    elif lint_level == 2:
        lint_banner = '<div class="call warnbox"><h3>Read the amber notes on the prompt cards before generating</h3><p>They are the words that seed bad clips. Most are one edit.</p></div>'

    t2v = [p for p in ai if p["frames"] == "none"]
    framed = [p for p in ai if p["frames"] != "none"]
    if framed:
        frames_block = f'''<h3>The look — pasted onto every image prompt</h3>
    <p>Same film, same lens, same four colours pulled from her set, same rule about faces. Generate the start frames in <b>one ChatGPT conversation</b> so it holds the style; if one drifts, say &ldquo;same style as the previous image&rdquo; and regenerate. <b>Iterate the picture, not the video</b> — images are cheap. Count the people and objects, check hands and edges, look for anything modern, and only then animate.</p>
    <button class="ptext" data-copy="{esc(STYLE_IMAGE)}">{esc(STYLE_IMAGE)}<span class="copyhint">copy</span></button>'''
    else:
        frames_block = f'''<h3>Every clip here is text to video</h3>
    <p>No start frames on this episode: each card below is <b>one prompt</b>, pasted into Veo, and a clip comes back. That is why the prompts read as shots rather than as lists of prohibitions — the pile of negatives exists to stop a model contaminating an image you handed it, and with no image to protect it only suppresses motion. Take two outputs per card and keep the one with more life in it, not less.</p>
    <p>What is appended to every prompt is only what is true of every shot on this channel: one continuous take, photographic realism, no on-screen text, and silent — Veo generates audio natively and it will score your clip if you let it. Anything a particular shot must not show — a resolved face, a modern object, an animal — is written into that card, because a guard only means something when the shot it guards is on the page beside it.</p>
    <button class="ptext" data-copy="{esc(STYLE_VIDEO_NOFRAME)}">{esc(STYLE_VIDEO_NOFRAME)}<span class="copyhint">copy</span></button>'''
    if framed:
        motion_block = f'''<p><b>The video prompt animates what is already in the picture. It never introduces anything.</b> Every noun in the motion prompt is already in the image prompt. Each prompt names the one thing that moves, says what stays still, and closes with what must not appear. This guard rail is appended to every one:</p>
    <button class="ptext" data-copy="{esc(STYLE_VIDEO)}">{esc(STYLE_VIDEO)}<span class="copyhint">copy</span></button>
    <p><b>In Flow, for the cards with a start frame:</b> Frames to Video &rarr; upload the start frame (and the end frame only where the card says so) &rarr; paste the video prompt &rarr; 16:9 &rarr; two outputs, keep the calmer one &rarr; upscale the keeper to 1080p &rarr; save as <code>ai/&lt;id&gt;.mp4</code>.</p>'''
    else:
        motion_block = f'''<p>One motion carries a shot. Name what moves, let everything else hold, and keep the camera locked off or on a push of a few percent — those are the two things a video model still gets wrong often enough to matter, and they are in the guard table below whether or not there is a start frame to protect.</p>
    <p><b>In Flow:</b> text to video &rarr; paste the whole prompt from the card &rarr; 16:9 &rarr; two outputs &rarr; upscale the keeper to 1080p &rarr; save as <code>ai/&lt;id&gt;.mp4</code>.{" A card marked <b>attach</b> goes in through Ingredients instead, with the reference image added, and the same prompt." if ep.references else ""} The clip comes back eight seconds long whatever the card asks for (ten from the Gemini app); the duration on the card is how long it should be ON SCREEN once trimmed.</p>'''
    motion_h3 = "The one rule for motion prompts"
    if only_all:
        # Daring takes only (S2E9): the locked-off, one-motion discipline is what the daring take lifts, so the box says
        # how to make them instead, and the hero box (which lifts some of that discipline for one clip) has nothing to do.
        frames_block = f'''<h3>Every clip here is a daring take, text to video</h3>
    <p>No start frames and no safe takes on this episode: each card below is <b>one prompt</b>, with the reference images of
    whoever recurs in the shot attached to it, and a clip comes back. The prompt is the shot as a film would shoot it —
    who is in it and what is on their faces, what moves, where the camera goes, the light — in plain positive words.</p>
    <p>What is appended to every prompt is only what is true of every shot on this channel: one continuous take,
    photographic realism, no on-screen text, and silent — the generators make audio on their own and will score the clip
    if you let them. Anything a particular shot must not show is written into that card.</p>
    <button class="ptext" data-copy="{esc(STYLE_VIDEO_DARING)}">{esc(STYLE_VIDEO_DARING)}<span class="copyhint">copy</span></button>'''
        motion_h3 = "How to make them"
        motion_block = f'''<p><b>In the Gemini app:</b> attach the images the card names &rarr; paste the whole prompt from the card &rarr; 16:9 &rarr; three or four outputs &rarr; keep the one that holds together &rarr; save as <code>ai/&lt;id&gt;.mp4</code>. <b>In Flow:</b> Ingredients, not Frames, with the same images and the same prompt — it takes three images, so a card that attaches four goes to the Gemini app. A new chat for each card, so one clip's people never leak into the next.</p>
    <p>The clip comes back eight seconds long from Flow and ten from the Gemini app, whatever the card asks for; the duration on the card is how long it should be ON SCREEN once trimmed.</p>'''
        hero_box = ((f'<p class="fine"><b>{esc(hero["title"])}</b> is the hero — the shot the episode most needs, so it is '
                     f'first in line and worth the most outputs.</p>') if hero else "")

    generate = f'''
  <div class="sect-head" id="generate">
    <h2>{'1 · ' if plan_first else ''}Generate — AI clips</h2>
    <p>{len(ai)} clips, about {sum(int(str(p["dur"]).rstrip("s")) for p in ai)} seconds of generated footage. Bible and history scenes only — no still lifes.
    Every copy button already has the style block appended. Priority order below; if you only make some, make them from the top.</p>
  </div>
  {lint_banner}
  <div class="stylebox">
    {frames_block}
    <h3>{motion_h3}</h3>
    {motion_block}
    <details><summary>What seeds a bad generation — the guard table</summary>
      <table class="guards"><thead><tr><th>If the prompt has&hellip;</th><th>You get&hellip;</th><th>So&hellip;</th></tr></thead><tbody>{guards}</tbody></table>
    </details>
    {hero_box}
  </div>
  {refs_block}
  {daring_box}
  {prompts}'''

    retrieve_intro = (f'{n.get("picture",0)} pictures. Each one sits in the corner over her left shoulder for four to six seconds so the audience can place a name or a thing she is talking about. Download the file, save it under the name on the card, and it comes back framed as an overlay — same corner, same shadow, every time.'
                      if not (pictures and got_n == len(pictures)) else
                      f'{len(pictures)} pictures, already downloaded and framed into the pack — nothing to fetch. Each card says '
                      f'where its file came from, what it renders as, and anything the video description owes.')
    retrieve = f'''
  <div class="sect-head" id="retrieve">
    <h2>{'2 · ' if plan_first else ''}Retrieve — pictures over her shoulder</h2>
    <p>{retrieve_intro}</p>
  </div>
  <div class="call"><h3>Before the rights question: does the viewer know what they are looking at?</h3>
  <p>{esc(SAYS_WHAT_IT_IS)} They get five seconds and no second chance. A picture nobody can place is not context —
  it is a puzzle they solve instead of listening, and it costs more than an empty corner would have.
  That makes the credit line a <b>caption first, attribution second</b>: it says what the thing is, not who owns it.
  {esc(CAPTION_RULE)}
  Licence attribution — photographer, licence, link — goes in the video description, which is the normal way to
  attribute Creative Commons material in a video.</p></div>
  <div class="policy two-col">
    <div><h4>Yes</h4><ul>{policy_yes}</ul></div>
    <div><h4>Never</h4><ul>{policy_no}</ul></div>
  </div>
  {policy_sens}
  <h4 class="srchead">Where a picture may come from, best first</h4>
  <div class="tablewrap"><table class="sources">
    <tbody>{"".join(f'<tr><td>{esc(v[0])}</td><td>{esc(v[2])}</td><td><span class="rights r-{esc(v[1])}">{esc(v[1])}</span></td></tr>' for k, v in RIGHTS.items() if k != "no")}</tbody>
  </table></div>
  <p class="fine">An editorial risk policy, not legal advice. A picture used to comment on the thing it comes from is the strongest case; a picture used as decoration is the weakest.</p>
  {pics}
  {'<div class="call"><h3>Not pictured — on purpose</h3><ul class="nots">'+nots+'</ul></div>' if nots else ''}'''

    punch = f'''
  <div class="sect-head" id="punch">
    <h2>Punch-ins — candidates for Katrina</h2>
    <p>{len(punches)} moments where the line lands on her face and a tighter framing helps it. Two framings only — as shot, and about 115% with her eyes at the same height. Never a slow zoom, never during a clip, a picture or a dim. A punch-in also hides a jump cut, so where a retake was trimmed near one of these, put the cut there.</p>
    <p><b>Each one is two phrases, because in Descript it is two scene breaks.</b> Ctrl-F the <i>tighten on</i> phrase and type <code>/</code> a word before it; Ctrl-F the <i>release on</i> phrase and type <code>/</code> just before it. <b>Put both breaks in before you resize anything</b> — a scene you split keeps the framing it was split from, so tightening first means the release comes out tight too. Then click into the scene between the two breaks, select her video, and in Properties → Size &amp; Position, with the link on, make it 15% bigger (1920 wide becomes 2208) and nudge it until her eyes sit where they were. Leave <i>Apply to all scenes</i> off, or the whole episode tightens. The punch is the scene between the breaks — which means it ends where you decided it ends, rather than running on to whatever the next break happened to be.</p>
  </div>
  <ol class="punches">{punch_rows}</ol>'''

    cues_block = f'''
  <div class="sect-head" id="cues">
    <h2>{'3 · ' if plan_first else ''}Cue sheet</h2>
    <p>{'Keyed to script beats for now — the phrases and the timecodes arrive with the transcript, and the overlays get rendered then.' if state == 'plan' else 'Work top to bottom. Tick each cue as it is placed; ticks are saved in this browser.'}</p>
  </div>
  <div class="cuewrap">
  <div class="controls">{chips}<span class="spacer"></span><span class="progress"><b id="done">0</b> / {len(ep.cues)} placed</span></div>
  {"".join(rows)}
  </div>'''

    body_order = [generate, retrieve, cues_block, punch] if plan_first else [cues_block, generate, retrieve, punch]

    corrections_block = f'''
  <div class="sect-head"><h2>Fix in the captions</h2></div>
  <div class="call"><h3>Names she says differently from how they are spelled</h3><ul class="nots">{corr}</ul><p>The overlays carry the correct spellings; the captions need the same fix.</p></div>''' if ep.corrections else ""

    title = f'{esc(m["code"])} {"Shot Plan" if state == "plan" else "Cue Sheet"}'
    key = f"ffr-{m['code']}-cues"
    return f'''<meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
{CSS}
</style>

<header class="top"><div class="wrap">
  <p class="eyebrow">{eyebrow}</p>
  <h1>{esc(m["title"])} — {"shot plan" if state == "plan" else "cue sheet"}</h1>
  <p class="lede">{lede}</p>
  {conv}
</div></header>

<div class="wrap">
  {"".join(body_order)}
  {corrections_block}
  {('<div class="sect-head"><h2>Notes on this cut</h2></div>' + notes) if notes else ''}
  <footer>
    {esc(m["code"])} · {esc(m["title"])}{(" · Descript composition " + esc(m["descript"].get("composition","")[:8])) if m.get("descript",{}).get("composition") else ""}<br>
    No stock footage — every cutaway is generated · No photographs of victims, ever<br>
    Progress ticks are saved in this browser only
  </footer>
</div>

<script>
(function(){{
  var KEY = "{key}";
  var state = {{}};
  try {{ state = JSON.parse(localStorage.getItem(KEY) || "{{}}") || {{}}; }} catch (e) {{ state = {{}}; }}
  var save = function(){{ try {{ localStorage.setItem(KEY, JSON.stringify(state)); }} catch (e) {{}} }};
  var doneEl = document.getElementById("done");
  var boxes = Array.prototype.slice.call(document.querySelectorAll(".tick input"));
  // Ticks belong to a cue, not to a position in the list (15 Oct 2026): a cue inserted mid-list used to shift every
  // tick below it onto the wrong cue. Each tick stores the cue's fingerprint, so a cue whose phrase or file changed
  // after it was placed shows as changed. Ticks saved by position are carried over once, exactly as they show now.
  if (state.__v !== 2) {{
    var moved = {{__v: 2}};
    boxes.forEach(function(b){{ if (state[b.dataset.n]) moved[b.dataset.id] = b.dataset.fp; }});
    state = moved; save();
  }}
  function refresh(){{
    var n = 0;
    boxes.forEach(function(b){{
      var s = state[b.dataset.id], on = !!s && s === b.dataset.fp, changed = !!s && s !== b.dataset.fp;
      var li = b.closest(".cue");
      b.checked = on; li.classList.toggle("done", on); li.classList.toggle("changed", changed); if (on) n++;
    }});
    if (doneEl) doneEl.textContent = n;
  }}
  boxes.forEach(function(b){{
    b.addEventListener("change", function(){{
      if (b.checked) state[b.dataset.id] = b.dataset.fp; else delete state[b.dataset.id];
      save(); refresh();
    }});
  }});
  refresh();
  var active = new Set();
  document.querySelectorAll(".filt").forEach(function(f){{
    f.setAttribute("aria-pressed","false");
    f.addEventListener("click", function(){{
      var k = f.dataset.kind;
      if (active.has(k)) {{ active.delete(k); f.setAttribute("aria-pressed","false"); }}
      else {{ active.add(k); f.setAttribute("aria-pressed","true"); }}
      document.querySelectorAll(".cue").forEach(function(c){{
        c.classList.toggle("hide", active.size > 0 && !active.has(c.dataset.kind));
      }});
      document.querySelectorAll(".grp").forEach(function(g){{
        g.hidden = (g.querySelectorAll(".cue:not(.hide)").length === 0);
      }});
    }});
  }});
  function copy(btn){{
    var t = btn.dataset.copy;
    var done = function(){{
      btn.classList.add("copied");
      var h = btn.querySelector(".copyhint"); var old = h ? h.textContent : "";
      if (h) h.textContent = "copied";
      setTimeout(function(){{ btn.classList.remove("copied"); if (h) h.textContent = old; }}, 1400);
    }};
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(t).then(done, function(){{ fallback(t, done); }});
    }} else {{ fallback(t, done); }}
  }}
  function fallback(t, cb){{
    var ta = document.createElement("textarea");
    ta.value = t; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try {{ document.execCommand("copy"); cb(); }} catch (e) {{}}
    document.body.removeChild(ta);
  }}
  document.querySelectorAll("[data-copy]").forEach(function(b){{
    b.addEventListener("click", function(){{ copy(b); }});
  }});
}})();
</script>
'''


CSS = r'''
:root {
  --bg:#EFEFEA; --surface:#FAFAF7; --raise:#FFFFFF;
  --ink:#1E1F1C; --ink-2:#4A4B45; --muted:#75766E;
  --rule:#DEDED6; --rule-2:#E9E9E2;
  --clay:#A8624A; --olive:#6E7350; --slate:#52687E; --amber:#B07A2A; --red:#A63D2F;
  --shadow:0 1px 2px rgba(30,31,28,.05), 0 8px 24px rgba(30,31,28,.05);
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --sans:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif;
  --disp:"Fraunces",Georgia,"Times New Roman",serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme:dark;
    --bg:#131412; --surface:#1A1B18; --raise:#212220;
    --ink:#E7E7E1; --ink-2:#B9BAB2; --muted:#8D8E86;
    --rule:#2B2C28; --rule-2:#242521;
    --clay:#C88266; --olive:#969B70; --slate:#8AA0B4; --amber:#D9A24A; --red:#D8705F;
    --shadow:0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.25);
  }
}
:root[data-theme="dark"] {
  color-scheme:dark;
  --bg:#131412; --surface:#1A1B18; --raise:#212220;
  --ink:#E7E7E1; --ink-2:#B9BAB2; --muted:#8D8E86;
  --rule:#2B2C28; --rule-2:#242521;
  --clay:#C88266; --olive:#969B70; --slate:#8AA0B4; --amber:#D9A24A; --red:#D8705F;
  --shadow:0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.25);
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased;padding:0 0 6rem}
.wrap{max-width:1080px;margin:0 auto;padding:0 clamp(1rem,4vw,2.5rem)}
a{color:var(--clay)}
header.top{border-bottom:1px solid var(--rule);margin-bottom:2rem}
header.top .wrap{padding-top:clamp(2.5rem,6vw,4rem);padding-bottom:2rem}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:0 0 1rem;display:flex;gap:.9rem;flex-wrap:wrap;align-items:center}
.eyebrow span{color:var(--clay)}
h1{font-family:var(--disp);font-weight:600;font-size:clamp(2.1rem,5.2vw,3.1rem);line-height:1.05;margin:0 0 .7rem;letter-spacing:-.015em;text-wrap:balance}
.lede{color:var(--ink-2);max-width:66ch;margin:0 0 1.6rem;font-size:1.02rem}
.lede strong{color:var(--ink);font-weight:600}
.conv{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:3px;overflow:hidden;margin-bottom:1.6rem}
.conv > div{background:var(--surface);padding:1rem 1.1rem}
.conv h4,.policy h4{font-family:var(--mono);font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 .5rem;font-weight:500}
.conv p{margin:0;font-size:.88rem;color:var(--ink-2);line-height:1.5}
.conv b{color:var(--ink);font-weight:600}
.conv code,.call code,.piccard code,.stylebox code{font-family:var(--mono);font-size:.85em;background:var(--rule-2);padding:.1rem .3rem;border-radius:2px;overflow-wrap:anywhere}
.controls{display:flex;gap:.45rem;flex-wrap:wrap;align-items:center;padding:.9rem 0;position:sticky;top:env(safe-area-inset-top,0px);z-index:20;background:var(--bg);border-bottom:1px solid var(--rule);margin-bottom:1.4rem}
.filt{font:500 .76rem/1 var(--sans);display:inline-flex;align-items:center;gap:.42rem;padding:.44rem .66rem;border:1px solid var(--rule);border-radius:999px;background:var(--surface);color:var(--ink-2);cursor:pointer;transition:border-color .12s,color .12s,background .12s}
.filt i{width:8px;height:8px;border-radius:2px;background:var(--hue);flex:none}
.filt b{font-family:var(--mono);font-weight:400;color:var(--muted);font-size:.72rem}
.filt:hover{border-color:var(--muted);color:var(--ink)}
.filt[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.filt[aria-pressed="true"] b{color:var(--bg);opacity:.6}
.filt:focus-visible,.anchor:focus-visible,.ptext:focus-visible,.tick:focus-within{outline:2px solid var(--clay);outline-offset:2px}
.spacer{flex:1}
.progress{font-family:var(--mono);font-size:.75rem;color:var(--muted);white-space:nowrap}
.progress b{color:var(--ink);font-weight:500}
.grp{margin:0 0 2.4rem;scroll-margin-top:4.6rem}
.grp-head{display:flex;align-items:baseline;gap:.9rem;flex-wrap:wrap;padding-bottom:.6rem;border-bottom:1px solid var(--rule);margin-bottom:.2rem}
.grp-head h2{font-family:var(--disp);font-weight:600;font-size:1.22rem;margin:0;letter-spacing:-.01em}
.grp-head p{margin:0;font-family:var(--mono);font-size:.74rem;color:var(--muted);letter-spacing:.01em}
.cues,.punches{list-style:none;margin:0;padding:0}
.cue{display:grid;grid-template-columns:auto 4.4rem 1fr;gap:.75rem;padding:.95rem 0 1rem;border-bottom:1px solid var(--rule-2);align-items:start}
.cue.hide{display:none}
.tick{display:flex;align-items:center;justify-content:center;padding-top:.16rem;cursor:pointer}
.tick input{position:absolute;opacity:0;width:0;height:0}
.tick span{width:15px;height:15px;border:1.5px solid var(--rule);border-radius:3px;display:block;background:var(--surface);transition:background .12s,border-color .12s}
.tick input:checked + span{background:var(--olive);border-color:var(--olive)}
.tick input:checked + span::after{content:"";display:block;width:4px;height:8px;border:solid var(--bg);border-width:0 1.6px 1.6px 0;transform:rotate(45deg);margin:1px 0 0 4.4px}
.cue.done .body{opacity:.42}
.cue.changed .body::before{content:"changed since you ticked it \2014  place it again";display:block;margin-bottom:.45rem;font:500 .68rem/1 var(--sans);letter-spacing:.04em;text-transform:uppercase;color:var(--clay)}
.tc{font-family:var(--mono);font-size:.82rem;color:var(--ink-2);padding-top:.1rem;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.tc.approx{color:var(--muted);font-style:italic}
.is-star .tc{color:var(--clay);font-weight:500}
.body{min-width:0;transition:opacity .15s}
.meta{display:flex;gap:.42rem;flex-wrap:wrap;align-items:center;margin-bottom:.42rem}
.chip{font:500 .68rem/1 var(--sans);letter-spacing:.05em;text-transform:uppercase;color:var(--hue);border:1px solid color-mix(in srgb,var(--hue) 40%,transparent);background:color-mix(in srgb,var(--hue) 9%,transparent);padding:.24rem .45rem;border-radius:3px}
.mode{font-family:var(--mono);font-size:.68rem;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);border:1px dashed var(--rule);padding:.22rem .42rem;border-radius:3px}
.mode-dim,.mode-cut{border-style:solid}
.dur,.asset,.prio{font-family:var(--mono);font-size:.72rem;color:var(--muted)}
.asset{background:var(--rule-2);padding:.2rem .4rem;border-radius:3px;color:var(--ink-2)}
.flag{font:500 .68rem/1 var(--sans);letter-spacing:.04em;text-transform:uppercase;padding:.24rem .45rem;border-radius:3px}
.flag-star{color:var(--bg);background:var(--clay)}
.flag-warn{color:var(--clay);border:1px solid var(--clay)}
.flag-pend{color:var(--amber);border:1px dashed var(--amber)}
.flag-hero{color:var(--bg);background:var(--slate)}
.flag-ref{color:var(--olive);border:1px solid var(--olive)}
.stylebox.refbox{border-left-color:var(--clay)}
.pbox.t2v.withref{border-color:var(--olive)}
.reflead{display:block;margin-bottom:.35rem;color:var(--olive);font-style:italic}
.refcard .frames a{color:var(--clay)}
.flag-daring{color:var(--clay);border:1px dashed var(--clay)}
.flag-made{color:var(--bg);background:var(--olive)}
.stylebox.daringbox{border-left-color:var(--amber)}
.daringbox .pbox{background:var(--surface)}
.daringbox .nots{margin:0;padding-left:1.05rem;font-size:.84rem}
.daringbox .pbox.refused{margin-top:.9rem;border-left:3px solid var(--clay)}
.pbox.t2v.daring{border-color:var(--amber);margin-top:.9rem}
.pbox.daring .plabel span{background:var(--amber)}
.herobox{margin-top:1rem;border:1px solid var(--slate);border-left:3px solid var(--slate);border-radius:0 4px 4px 0;padding:1rem 1.15rem;background:var(--raise)}
.herobox h4{font-family:var(--disp);font-size:1rem;font-weight:600;margin:0 0 .5rem;color:var(--ink)}
.herobox p{margin:0 0 .8rem;font-size:.88rem;color:var(--ink-2);line-height:1.6;max-width:74ch}
.herobox .pbox{background:var(--surface)}
.herobox .nots{margin:0;padding-left:1.05rem;font-size:.84rem}
.herobox .fine{margin:.8rem 0 0}
.anchor{display:block;width:100%;text-align:left;font-family:var(--disp);font-size:1.02rem;line-height:1.4;color:var(--ink);background:none;border:0;padding:.1rem 0;cursor:pointer;position:relative;font-weight:400}
.anchor .q{color:var(--muted)}
.anchor:hover{color:var(--clay)}
.copyhint{font-family:var(--mono);font-size:.62rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin-left:.55rem;opacity:0;transition:opacity .12s;vertical-align:.15em}
.anchor:hover .copyhint,.ptext:hover .copyhint,.anchor:focus-visible .copyhint{opacity:1}
.anchor.copied .copyhint,.ptext.copied .copyhint{opacity:1;color:var(--olive)}
.beat{margin:.1rem 0;font-family:var(--disp);font-size:1rem;line-height:1.4;color:var(--ink-2);font-style:italic}
.beatlabel{font:500 .62rem/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--amber);font-style:normal;margin-right:.6rem;vertical-align:.15em}
.note{margin:.42rem 0 0;font-size:.87rem;color:var(--muted);line-height:1.5;max-width:72ch}
.pic{margin:.35rem 0 0;font-size:.86rem;color:var(--ink-2)}
.rights{font:500 .66rem/1 var(--sans);letter-spacing:.05em;text-transform:uppercase;padding:.22rem .42rem;border-radius:3px;border:1px solid var(--olive);color:var(--olive);white-space:nowrap}
.r-avoid{border-color:var(--amber);color:var(--amber)}
.r-label{border-color:var(--clay);color:var(--clay)}
.r-never{border-color:var(--red);color:var(--red)}
.lint{margin:.5rem 0 0;padding:0 0 0 1.1rem;font-size:.82rem;line-height:1.5}
.lint li{margin:.15rem 0}
.l-error{color:var(--red)} .l-warn{color:var(--amber)} .l-info{color:var(--muted)}
.sect-head{scroll-margin-top:4.6rem;margin:3.4rem 0 1.4rem;padding-top:2.4rem;border-top:2px solid var(--ink)}
.sect-head h2{font-family:var(--disp);font-weight:600;font-size:1.7rem;margin:0 0 .5rem;letter-spacing:-.015em}
.sect-head p{margin:0;color:var(--ink-2);max-width:66ch}
.prompt,.piccard{background:var(--surface);border:1px solid var(--rule);border-radius:4px;padding:1.15rem 1.25rem 1.3rem;margin-bottom:1rem;box-shadow:var(--shadow)}
.prompt header,.piccard header{display:flex;align-items:baseline;gap:.7rem;flex-wrap:wrap;margin-bottom:.6rem}
.prompt h3,.piccard h3{font-family:var(--disp);font-size:1.1rem;font-weight:600;margin:0;letter-spacing:-.01em}
.prompt header .tc,.piccard header .tc,.punches .tc{color:var(--clay);font-weight:500}
.prompt .on{margin:0 0 .9rem;font-size:.84rem;color:var(--muted)}
.anchor.inline{display:inline;width:auto;font-size:.95rem;color:var(--ink-2)}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:.9rem}
.pbox{background:var(--raise);border:1px solid var(--rule-2);border-radius:3px;padding:.85rem .9rem}
.plabel{font-family:var(--mono);font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-2);margin-bottom:.55rem;display:flex;gap:.5rem;align-items:center}
.plabel span{color:var(--bg);background:var(--muted);padding:.14rem .38rem;border-radius:2px;font-size:.62rem;letter-spacing:.06em}
.ptext{display:block;width:100%;text-align:left;background:none;border:0;padding:0;cursor:pointer;font-family:var(--sans);font-size:.87rem;line-height:1.55;color:var(--ink-2)}
.ptext:hover{color:var(--ink)}
.stylenote{display:block;margin-top:.5rem;font-family:var(--mono);font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;color:var(--olive)}
.stylebox{background:var(--surface);border:1px solid var(--rule);border-left:3px solid var(--olive);border-radius:0 4px 4px 0;padding:1.1rem 1.25rem;margin-bottom:1.2rem}
.stylebox h3{font-family:var(--disp);font-size:1.05rem;font-weight:600;margin:0 0 .5rem}
.stylebox p{margin:0 0 .7rem;font-size:.88rem;color:var(--ink-2);line-height:1.6;max-width:74ch}
.pbox.t2v{border-color:var(--slate)}
.pbox.t2v .ptext b{font-weight:600;color:var(--ink)}
.stylebox .ptext{font-size:.86rem;color:var(--ink);background:var(--raise);border:1px solid var(--rule-2);border-radius:3px;padding:.75rem .85rem;margin:.3rem 0 .9rem}
.stylebox details{margin-top:.6rem;max-width:100%;overflow-x:auto}
.stylebox summary{cursor:pointer;font-weight:600;font-size:.9rem;color:var(--ink)}
.guards{width:100%;border-collapse:collapse;margin-top:.8rem;font-size:.84rem}
.guards th{text-align:left;font-family:var(--mono);font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:500;padding:.4rem .5rem;border-bottom:1px solid var(--rule)}
.guards td{padding:.5rem;border-bottom:1px solid var(--rule-2);vertical-align:top;color:var(--ink-2)}
.guards td:first-child{color:var(--ink);font-weight:500}
.frames{margin:.7rem 0 0;padding-top:.6rem;border-top:1px dashed var(--rule);font-size:.8rem;color:var(--muted);line-height:1.5}
.policy{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:3px;overflow:hidden;margin-bottom:1.2rem}
.policy > div{background:var(--surface);padding:1rem 1.1rem}
.policy ul,.policy ol{margin:0;padding-left:1.1rem;font-size:.86rem;color:var(--ink-2);line-height:1.5}
.policy li{margin:.2rem 0}
.policy.two-col{grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.fine{margin:.7rem 0 1.2rem;font-size:.78rem;color:var(--muted);line-height:1.55;max-width:74ch}
.srchead{margin:1.3rem 0 .5rem}
.tablewrap{overflow-x:auto;border:1px solid var(--rule);border-radius:3px;background:var(--surface)}
table.sources{width:100%;border-collapse:collapse;font-size:.86rem}
table.sources td{padding:.6rem .8rem;border-bottom:1px solid var(--rule-2);vertical-align:top;color:var(--ink-2)}
table.sources tr:last-child td{border-bottom:0}
table.sources td:first-child{color:var(--ink);font-weight:600;white-space:nowrap;width:1%}
table.sources td:last-child{width:1%;white-space:nowrap}
.piccard dl{display:grid;grid-template-columns:auto 1fr;gap:.35rem 1rem;margin:0;font-size:.88rem}
.piccard dt{font-family:var(--mono);font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);padding-top:.2rem}
.piccard dd{margin:0;color:var(--ink-2);min-width:0;overflow-wrap:anywhere}
.punches li{display:grid;grid-template-columns:4.4rem 1fr;gap:.2rem .75rem;padding:.8rem 0;border-bottom:1px solid var(--rule-2)}
.punches .why{grid-column:2;font-size:.86rem;color:var(--muted)}
.punches .rel{grid-column:2}
.punches li > .inout,.punches li > .anchor.inline,.punches li > i{grid-column:2}
.inout{display:block;font-family:var(--mono);font-size:.64rem;letter-spacing:.11em;text-transform:uppercase;color:var(--muted);margin:.35rem 0 .05rem}
.punches li > .inout:first-of-type{margin-top:0}
.punches .anchor.inline{font-size:1rem;color:var(--ink)}
.call{border-left:3px solid var(--clay);background:var(--surface);padding:1rem 1.2rem;border-radius:0 3px 3px 0;margin-bottom:1rem}
.call.err{border-left-color:var(--red)} .call.warnbox{border-left-color:var(--amber)} .call.sens{border-left-color:var(--slate)}
.call h3{font-family:var(--disp);font-size:1.05rem;font-weight:600;margin:0 0 .45rem}
.call p{margin:0 0 .6rem;font-size:.9rem;color:var(--ink-2);line-height:1.6;max-width:72ch}
.call p:last-child{margin-bottom:0}
.nots{margin:0;padding-left:1.1rem;font-size:.88rem;color:var(--ink-2);line-height:1.55}
.nots li{margin:.3rem 0}
footer{margin-top:3rem;padding-top:1.4rem;border-top:1px solid var(--rule);font-family:var(--mono);font-size:.73rem;color:var(--muted);line-height:1.7}
@media (prefers-reduced-motion: reduce){*{transition:none!important;animation:none!important}}
@media (max-width:600px){.cue{grid-template-columns:auto 3.7rem 1fr;gap:.55rem}.anchor{font-size:.96rem}.piccard dl{grid-template-columns:1fr}}
'''


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("episode"); ap.add_argument("--out"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--plan-first", action="store_true",
                    help="put Generate and Retrieve above the cue list even though the cues are anchored — "
                         "for the both-passes-in-one-run case, where the transcript exists but nothing has been made yet")
    a = ap.parse_args()
    ep = load(a.episode)
    for w in ep.warnings: print("WARN ", w)
    for e in ep.errors: print("ERROR", e)
    if ep.errors: sys.exit(1)
    report = lint(ep)
    for cid, rows in report.items():
        for lvl, msg in rows: print(f"{lvl:5} {cid}: {msg}")
    if worst(report) == 3 and not a.force:
        print("prompt lint errors — fix them or pass --force"); sys.exit(1)
    out = a.out or os.path.join("out", ep.code, "cuesheet.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    page = build(ep, report, plan_first=True if a.plan_first else None)
    open(out, "w").write(page)
    print(f"wrote {out} ({len(page)} bytes) — state: {ep.state}, {len(ep.cues)} cues")
