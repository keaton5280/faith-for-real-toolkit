# visual-pipeline — Faith for Real episode visuals toolkit

The code behind the episode cue sheets and asset packs. One episode file in, three things out:
a cue sheet page (shot plan before the transcript, cue sheet after), the rendered overlay PNGs,
and the framed pictures. The house style lives in one place and never gets restated per episode.

**Where it lives (since 15 Oct 2026):** the private GitHub repo `keaton5280/faith-for-real-toolkit` is the source of
truth — clone it, change it, commit and push. `claude/visual-pipeline/bundle.md` in the YouTube Analytics project is a
fallback snapshot of the same files for a session that can't attach the repo: after every push, run
`python3 make_bundle.py pack` and `project_write` the new bundle.md (and this README to
`claude/visual-pipeline/README.md`) so the two never drift.

```
characters.py     standing characters — reference images made once and attached in every episode (Jesus made;
                  Saul and Samuel designed for S2E9, waiting on their images)
style.py          palette, type, PiP corner, AI look (STYLE_IMAGE / STYLE_VIDEO), GUARDS table,
                  cue kinds and quotas, the picture rights ladder and policy
episode.py        load(path) — validates an episode file, fills defaults, warns on quotas
lint_prompts.py   the hallucination-seed linter for AI prompts (run before publishing a shot plan)
check_anchors.py  verifies every anchor is verbatim and occurs exactly once in the transcript
overlays.py       the overlay builders — scripture, quote, names, name, stat, figures, timeline, kinetic
framing.py        frames a retrieved picture into the over-the-shoulder corner (was pip.py — renamed 15 Oct 2026
                  because it hid the real pip from `python3 -m pip` run in this folder)
maps.py           map cues — coastline, cities, a dotted line that travels; PNG steps + alpha .mov
charts.py         chart cues — an org chart (a tribune and his garrison), revealed a rank at a time
setup_geo.py      fetches and clips the Natural Earth coastline into geo/med.json (idempotent)
render.py         episode → out/<code>/overlays/*.png + README.md + MANIFEST.txt (+ check-*.png and check-phone-*.png
                  over a frame grab: every file, at full and at phone size)
cuesheet.py       episode → out/<code>/cuesheet.html (publish this as the artifact)
setup_fonts.py    fetches EB Garamond + Inter into fonts/ (idempotent)
episodes/         one file per episode; _template.py is annotated; S2E3.py is the worked example
```

## Setup (fresh session)

```
git clone https://github.com/keaton5280/faith-for-real-toolkit pipeline && cd pipeline   # private: add_repo it first
python3 setup_fonts.py                 # only if fonts/ is empty; installs fonttools + brotli itself if missing
python3 setup_geo.py                   # only if the episode has a map cue
pip install pillow numpy --break-system-packages   # normally already present
```

## Per episode

```
cp episodes/_template.py episodes/S2E4.py     # then fill it in from the script
python3 episode.py episodes/S2E4.py           # validate: errors, quota warnings, state
python3 lint_prompts.py episodes/S2E4.py      # fix every WARN on the AI prompts before publishing
python3 cuesheet.py episodes/S2E4.py          # → out/S2E4/cuesheet.html  (shot plan while anchors are None)
# … transcript lands: add anchor + tc to every cue, CORRECTIONS …
python3 check_anchors.py episodes/S2E4.py transcript.txt --fix     # rewrite anchors to her exact wording, re-check
python3 check_anchors.py episodes/S2E4.py transcript.txt --strict  # the gate: exits 1 unless every phrase is exact + unique
python3 render.py episodes/S2E4.py --pictures pictures/raw --check frame.jpg
python3 cuesheet.py episodes/S2E4.py          # → same page, now the cue sheet; republish to the same artifact

# both passes in one go (transcript arrived, nothing generated yet): add --plan-first so the
# Generate and Retrieve sections stay on top of the anchored cue list
python3 cuesheet.py episodes/S2E4.py --plan-first
```

**Her frame.** `--check` lays every file over `frame.jpg`, a still of Katrina in the recording chair, kept in the
channel folder on dadtop (`FaithForReal\frame.jpg`) and staged with the pictures. It came from S2E9's Descript share
on 15 Oct 2026: the share page's `og:video:url` is an HLS stream, and dadtop's ffmpeg (`C:\ffmpeg\bin`) takes one
frame from it at a moment with nothing on screen —
`ffmpeg -ss 420 -i "<og:video:url>" -frames:v 1 -vf scale=1920:1080 -q:v 2 frame.jpg`. If the set changes, take a
new one the same way; the workspace itself can't reach Descript's hosts.

`out/S2E4/` (overlays/, README.md, MANIFEST.txt) is the asset pack. It goes to `<PROJECT_FOLDER>\S2E4-assets\` on
dadtop — `PROJECT_FOLDER` is set once in `style.py` and is currently
`C:\Users\keato\OneDrive\Documents\Claudjects\FaithForReal`. Every render rebuilds `overlays/` from scratch and swaps it
in only when the whole run has succeeded, so a removed cue's file is gone from the pack; MANIFEST.txt lists exactly what
is in it, and on dadtop anything in `overlays\` that the manifest doesn't list goes to `_superseded\` before unzipping.

## Changes on 15 October 2026 (from the review of the kit)

- **Cue-sheet ticks follow the cue, not its position.** They were saved by position, so a cue inserted mid-list (S2E8's
  gate clip on 8 Oct) shifted every tick below it onto the wrong cue. Each tick now stores the cue's id and a fingerprint
  of its phrase and file; a cue that changed after it was ticked shows as changed and unticked. Old ticks carry over once.
- **`pip.py` is `framing.py`.** A file named pip.py in this folder made `python3 -m pip` run it instead of pip, so
  setup_fonts' install step did nothing; setup_fonts also checked for fontTools but not brotli, which woff2 needs.
- **`check_anchors.py`** counts a phrase that is unique but worded differently from the transcript as a difference, not
  a pass; prints the transcript's hash so a report says which export it checked; `--fix` re-checks after rewriting; and
  `--strict` (the gate before publishing) exits 1 unless every phrase is exact and unique.
- **`episode.py`** errors on a duration it can't read ("9", "9 sec") — the spacing check used to count it as zero. A
  punch can say how long it holds (`dur="6s"`). The minimums are gone from the quotas (ceilings stay); the one floor is
  something changing on screen in the first minute. And it warns on reading load — see below.
- **`render.py`** builds into a staging folder and swaps in on success, writes MANIFEST.txt, warns when two raw files
  share a picture's name, lists a map's motion file only if it was actually made (`maps.py` deletes a half-written
  one), warns on a verse fitted too small for a phone, and `--check` now composites every file at full and phone size.

## Reading load (added 15 October 2026)

A text card is read while she keeps talking. `episode.py` warns when a scripture, quote or timeline card asks for more
than 17 characters a second while she says something else, or 20 while she paraphrases it; a card she reads out word for
word is exempt, and so is a highlight step on a verse already up. Measured on S2E3–S2E9, 29 of 87 cards ran over 17 a
second, and the worst — S2E7's 2 Kings 14:26–27, 43 words in 9 seconds — was also fitted at 48 px, because the fitter
shrinks a long verse to make it fit. `render.py` warns below `READ['verse_min_px']` (56 px, about 11 pt on an upright
phone). The fix is editorial — cut the excerpt to the clause she is making, split it, or hold it longer — so these are
warnings, not errors. Thresholds are `READ` in style.py.

## Map cues

A `map` cue draws the coastline she is talking about and walks a dotted line between the places she
names. Places are `(name, lon, lat, label side)` — longitude first, the way GeoJSON has it — and
`context` holds places shown in grey for orientation but not on the route. It renders TWICE from one
drawing: cumulative PNG steps (`<id>-1.png` … `<id>-n.png`), placed exactly like kinetic text so the
line reaches each city on her word for it, and `<id>.mov`, a silent QuickTime Animation file with a
real alpha channel that travels on its own clock. (It was a VP9 WebM first; Descript imported that as
a black rectangle. qtrle is lossless RGBA, about 2 MB for six seconds, and decoded by everything.) Steps when she names the places in one sentence; the WebM
under a longer passage. `mode="pip"` puts it in the picture corner on the same shelf with the same
caption; `mode="full"` fills the frame on the dark ground. Everything about the look is MAP in
style.py. A motion file takes about thirty seconds to render, so `motion=False` skips it.

## Clips are text to video

Standing decision (2026-09): every AI clip is written for Veo text to video — one prompt in, a clip
back, no ChatGPT start frame. `CLIP_FRAMES_DEFAULT` in style.py is `"none"` and a new `ai` cue gets
that unless it asks for `frames="start"`. Write those prompts POSITIVELY, as a shot — subject,
action, camera, light — because the negative-heavy discipline exists only to stop a model
contaminating an image you handed it, and with no image it just suppresses motion. What gets appended is deliberately small: `STYLE_VIDEO_NOFRAME` carries only what is true of every
shot (one take, no camera move, photographic realism, no on-screen text, silent — Veo generates
audio natively). Everything else is per cue, in `guards`, and only where the shot could actually
break it: `"faces"`, `"christ"`, `"modern"`, `"hands"`, `"animals"`, `"crowd"`, or a sentence of
your own. A guard a shot cannot break is noise — "never a depiction of Jesus" on an empty shoreline
spends the model's attention on something the prompt was never going to produce. And the PERIOD
belongs in the shot description, named concretely ("first-century Judea", "Rome around AD 62", "a
red tunic and segmented iron armour"): "period-accurate" means nothing to a model that was never
told which period. The cue sheet's Generate section adapts: with no start-frame cards
it drops the ChatGPT half entirely.

## Character references (added for S2E7, Jonah)

When the same person is in several clips, text alone invents a slightly different man every time. One
reference image fixes that: declare it in the episode's `REFERENCES` (id, name, prompt — `file` defaults to
`ai/ref-<id>.png`) and give each clip he is big enough to recognise in `refs=("<id>",)`. It is a reference,
not a start frame — Flow's Ingredients mode, or an attachment in the Gemini app (Gemini Omni since 2026) —
so it fixes what he looks like and leaves the shot to the words; the text-to-video decision stands. On this
channel it is a COSTUME reference, never a portrait: full length, from behind, hood up, plain backdrop,
because the clips never show a face and a reference with one invites the model to turn him round. The cue
sheet puts the reference card at the top of Generate, flags every card that attaches it, and prepends two
sentences: `REF_INTRO` (the reference is an AI-generated character design, not a photograph of a real person — the
Gemini app otherwise takes a photographic face for a real one) and `REF_LEAD` (who he is and what to keep). Up to S2E8
the rest of each prompt still described him in the same words, so deleting those two sentences turned the card back into
plain text to video. From S2E9 the prompt only names him — see "Named, not described" below.

## Daring takes (added for S2E7, at Keaton's request)

Any `ai` cue can carry `daring=dict(image=…, video=…, refs=…, guards=…)`: the same beat shot the way a film would
shoot it — the face on screen, the camera moving, the animal in frame, hands doing things, several motions, the full
length. The safe take stays on the card unchanged; the daring one sits under it, is saved as `ai/<id>-daring.mp4`, and
the editor keeps whichever holds together. What is lifted and what is still held is `DARING` in style.py; the appended
block is `STYLE_VIDEO_DARING` (the safe block without the camera limit). A daring take of a recurring character attaches
the FRONT reference as well as the back one, and its lead sentence (`REF_LEAD_DARING`) asks the model to keep his face
and hair — the only reason a face reference exists. `lint_prompts.py` reports what a daring take attempts as INFO, and
still holds the channel's own lines (legible text, modern objects) exactly as on the safe take. A reference that
shows the face on a safe take is a warning. The face rule is recorded as Katrina's: she sees a face clip before one goes in.

What the generator refuses is a different list from what the house allows (`DARING["refused"]`). The Gemini app turned
down S2E7's first overboard take twice — "I can't make videos of real people in situations like that" (the photographic
face in the reference), then "dangerous situations" — because it put a recognisable man in mortal danger on screen:
held by four sailors, thrown into a storm sea, gone under a wave. `lint_prompts.py` now flags that (`PERIL`): WARN when a
face reference is attached, INFO otherwise. The way round it is the cut. A daring take can carry
`then=dict(image=…, video=…, cut_on="toss him", refs=…)`, a second shot the edit cuts to on her word: the moment before
with his face, the moment after without him, saved as `ai/<id>-daring-2.mp4`. And arguing in the chat changes nothing —
the chat agrees and the filter does not — so every try starts a new chat.

## Jesus on screen (2026-10-07)

Jesus may be depicted in generated clips wherever the story calls for it — Keaton, 2026-10-07: "I never banned
depictions of Jesus." Earlier versions of this toolkit read his 2026-09-24 answer ("Depictions of Jesus are fine") as
covering public-domain paintings only and kept a clip ban nobody had asked for: `lint_prompts.py` made every mention of
him an ERROR. That is gone (`DEPICT_CHRIST_IN_CLIPS = True` in style.py). In a clip he is a recurring character like
Peter or Jonah: he gets reference images (ids `jesus-…` in REFERENCES), and the linter now checks for consistency
instead — a clip that shows him with no Jesus reference attached is a WARN, a clip that shows him AND carries the
`christ` guard is a WARN (one of them is wrong), and a clip with his reference attached is INFO. The `christ` guard
stays for a shot written to keep him out of frame, as a choice for that shot. The safe-take face rule applies to him
as to anyone.

## Standing characters (added 2026-10-07)

An episode's own `REFERENCES` are for someone who belongs to that episode — S2E7's Jonah, S2E8's Peter. A standing
character is someone the channel keeps: his reference images are made once, live in their own folder in
`PROJECT_FOLDER`, and every episode attaches the same files, so he is the same man in every clip the channel ever
makes. They are declared in `characters.py`, and an episode does not declare them at all: a clip that names one of
their reference ids in `refs=(…)` (or in its daring take) gets it — `episode.py` resolves it, `lint_prompts.py` sees
it, and the cue sheet shows a **standing character** card with the files to attach and the character's description —
since S2E9 the fallback for a clip made without his images, not something pasted into every prompt.

Jesus is the first: `FaithForReal\Jesus_Character_Design\`, five views made in ChatGPT on 2026-10-07 —
`jesus-back` (full length from behind, face hidden: safe takes, and every daring take he is in), `jesus-front` (full
length, three-quarter front: daring takes, always with the back view), `jesus-face` (head and shoulders: daring takes
where his face is the shot), and `jesus-profile` and `jesus-full-front` for the Gemini app, which takes five references
where Flow's Ingredients takes three. With Peter in the same shot, give the slots to whoever is closest to the camera
and describe the other in words.

## Character models before the images exist (added for S2E9: Saul and Samuel)

A standing character can be declared before he is made: `made=None`, `description=None`, and `design=dict(lineup=…,
views=…)` — the two ChatGPT prompts Jesus was made with, a lineup of four to choose the man from and then his five views
and a paragraph in the same chat. The file names are fixed in advance (`<name>-back.png`, `-front`, `-face`, `-profile`,
`-full-front`, in `<Name>_Character_Design\`), so clips attach them by id before they exist. `views_prompt()` and
`view_refs()` in characters.py write the second prompt and the five ids the same way for everyone.

The cue sheet gives each standing character ONE card, however many of his views the episode attaches: the files and
the clips that use each, then either his description (made) or the two prompts (not yet), with where to save the set.
When the images come back, set `made` to the date, give `view_refs()` the five file names ChatGPT chose (it numbers them
-1 to -5 in the order of the prompt: back, front, face, profile, full front), and set `description` to the paragraph
verbatim — or, if none came back, write it from the images and save it beside them as `<Name>_Character_Description.txt`,
as was done for Saul and Samuel (made 2026-10-13). The paragraph does not go into the prompts (next section).

`tag` ("very tall man in the deep purple robe") is how the lead sentence tells two people apart when both are attached
to one clip — "The man in the reference images is Saul" would fit either of them, so with two people attached each
sentence names its man by what he is wearing.

## Named, not described (added for S2E9, at Keaton's question)

"Why do I include character models in the Gemini prompts if you're just going to describe the characters in the prompt
as well?" — he was right. The images carry the look; the words only have to say who is who and what this scene changes.
With `EPISODE["people_in_prompts"] = "named"` (the template's default; episodes before S2E9 have no key and read as
"described"), a prompt names each attached person in a few words — "Saul, in his deep purple robe" — and states plainly
anything the scene does to him that the images don't show: a borrowed cloak over the robe, a hood up, a hem made plain to
see. Pasting the whole description as well was mostly repetition, and wherever the words and the pictures disagreed it
handed the model two answers. On a named episode:

- every clip card with images attached ends with the fallback: *without the images, delete the first N sentences and
  paste his description from his card in their place* (`without_images()` in cuesheet.py);
- the standing-character card labels the description "only for a clip made without his images";
- `lint_prompts.py` warns when any sentence of an attached person's description turns up verbatim in a prompt.

Described episodes (S2E7, S2E8) render exactly as before.

## Daring takes only (added for S2E9, at Keaton's request)

An `ai` cue with `daring=dict(…)` and no `image`/`video` is a clip that is a daring take and nothing else. `episode.py`
marks it `daring_only`; its card shows the daring take alone, saved as `ai/<id>.mp4` (a second shot as `ai/<id>-2.mp4`);
`lint_prompts.py` lints it by the daring rules only; and the over-six-seconds warning does not apply, since a daring
take uses the full length the model hands back. When every clip on an episode is daring-only, the Generate section
explains how to make daring takes instead of the safe-take discipline, the hero box shrinks to one line, and the
references block introduces the people who recur. A card that attaches four images says Gemini app: Flow's Ingredients
takes three — on a second shot (`then=`) as well as the first.

A daring-only clip's `dur` is its time on screen, capped at what the Gemini app hands back: 10 s for one shot, 20 s for two
(`then=dict(…, cut_on=…, dur=…)`). The S2E9 séance is the example — shot 1 in on the scream, the cut to shot 2 on "Saul
asks what she sees", 19 s to the bow. `check_anchors.py` now checks every phrase Keaton Ctrl-Fs, not only anchors and
release phrases: a second shot's `cut_on` and a picture's arrow `anchor` too (reported as `(cut)` and `(arrow)`; `--fix`
leaves those two to be corrected by hand).

## Picture links (added for S2E7)

A picture cue can carry `link="https://…"` when the exact page is already known — a museum object page, a Commons
file, a 3D model. The card's "search →" becomes "open →" and goes straight there, and the asset-pack README lists it
under the picture. Without it the card still builds a search from `search` (Commons for pd/cc, Google Images
otherwise). A 3D scan published under CC BY (Sketchfab, Zenodo) is a usable `cc` source for an object no photographer
has licensed openly: a head-on render of the model is the picture, and the licence credit goes in the description.

## Pictures already downloaded (added for S2E9)

When Claude downloads and frames the pictures itself (S2E9: on dadtop, because the workspace cannot reach Wikimedia or
the museums), the picture cue records it: `retrieved=dict(on="13 October", file="pic-….jpg", size="…", owe="…")`, and
`link` points at the exact file page it came from. The card then says "Got it" and "Saved as" instead of "Find it" and
"Save as", `owe` is printed as the line the video description owes (a photographer's CC BY credit), the eyebrow counts
pictures framed rather than pictures to find, and with every picture in, the plan-first lede and the Retrieve intro say
so. Wikimedia now answers scripted downloads of ORIGINAL files with 429 ("contact bot-traffic@wikimedia.org"), while its
thumbnails (`prop=imageinfo&iiurlwidth=1920` or `3840` — the standard steps) come through: take a thumbnail at 1920 for a
corner picture and 3840 for a full-frame one. A gigapixel original (the KHM Bruegel is 46,391 px wide) is only ever
taken as a thumbnail. A photograph of a framed painting comes in with `crop=` inside the frame, read off the corners.
Staged files sit under `/mnt/user-data/uploads/…`, not in `pictures/raw/`, so pass that folder: `render.py --pictures DIR`
and `arrowgrid.py <id> --pictures DIR`.
A scan someone has cut out of its page — the paper made transparent, as Commons' Dictionnaire infernal engravings
are — takes `matte="paper"`: it is set back on a warm page tone (`MATTE['paper']`) before framing, so it reads as a
page of an old book, not black lines floating on her wall (S2E9's Astaroth).

## Pictures across the bottom (added for S2E7)

`mode="strip"` on a picture lays it across the bottom of the frame, over her, with her face still in shot above it —
for a frieze or a panorama about four times as wide as it is tall, which the corner shrinks to a sliver and full frame
leaves mostly dark (Keaton's idea, for the Ashurnasirpal reliefs at 4.7 to 1). The width is the frame less two margins;
a picture that would come out taller than `STRIP['max_h']` is scaled down and centred instead. Same card, shadow and
hairline as the corner; the caption sits under it, flush left, like a museum label. Look is `STRIP` in style.py.

Two framing fixes came with it. A full-frame picture now fits the space ABOVE its caption, which sits under the
picture's own right edge — the Heemskerck engraving filled the frame and the caption landed on it, light type on a light
print. Full-frame maps keep the caption in the corner on their dark sea (`credit_below=False`), so they render exactly as
before. And `matte="knockout"` on a picture with a flat COLOURED surround — a 3D viewer's grey, a museum backdrop —
drops it too (`MATTE['surround_tol']`); tight on purpose, because on the relief 18 cleared the grey and 28 ate the stone.
Trim still only takes a white or black mount, so cream paper beyond a print's plate comes off with `crop=` on the cue.

## Generated pictures carry their prompt (added for S2E7)

A picture with `rights="gen"` — a reconstruction, made by an image model rather than found — can carry `prompt=…`. The
card then says "Make it" with a copy button (the prompt plus `STYLE_IMAGE`, the house look) instead of "Find it" and a
search link, and the asset README lists it as made, not found. `episode.py` warns on a gen picture with no prompt and no
file, and errors on a prompt without `rights="gen"`, which is what puts the word "reconstruction" on screen.

## Putting a clip in the corner

Keaton can lay a video over her footage in the editor and resize it into the corner by hand, which
is how the S2E5 maps actually shipped — two clips he made in Gemini, scaled down beside her. That
is `mode="pipclip"` on an `ai` cue, and it is worth knowing for three reasons: a corner video needs
no alpha channel, anything explanatory that moves can sit beside her instead of replacing her, and
a generated clip is no longer only a full-frame cutaway. A map or chart cue can feed the same path
with `tile_video=True`, which writes `<id>-tile.mp4` — the graphic alone, opaque, at tile size.

## Chart cues

A `chart` cue draws a chain of command and reveals it a rank at a time, for the sentences where she
stops to explain who outranks whom. `nodes=[dict(label=…, sub=…, icons=n)]`, top rank first; it
renders one cumulative PNG per rank, placed exactly like kinetic text, so the rank below arrives on
her word for it. The figures are geometric on purpose — the point is a count and a chain of command,
not a likeness, which is also what keeps it inside the picture policy (a diagram Claude can draw).
The whole assembly is measured and scaled to fit the card before anything is drawn, and it is
centred once for every step, so a rank never moves between frames. Look is `CHART` in style.py.

## Regression

`episodes/S2E3.py` rendered through this toolkit is pixel-identical to the overlays that shipped for
S2E3 (33/33 files). If you touch overlays.py, re-render S2E3 and diff before trusting the change. (Checked again on
15 Oct 2026 after `VERSE_FIT` was pulled out of `scripture()`: identical.)
The S2E8 cue sheet is the other check: the S2E9 changes left `cuesheet.py episodes/S2E8.py` byte-identical, with and
without `--plan-first`, and the S2E8 asset README too. A change that is meant to touch only new episodes should keep it so.
The 15 Oct 2026 changes touch every page on purpose (each tick carries its cue's id and fingerprint, and the page
declares utf-8), so the S2E8 page was tested in a browser instead: ticks made on the old page carry over to the same
cues, survive a cue inserted above them, and a cue whose phrase changes shows as changed.

## The bundle (changed for S2E9; a fallback since 15 Oct 2026)

Since the toolkit moved to GitHub, the bundle is the fallback, not the source — repack it after every push.
`bundle.md` in the project is a gzip+base64 tarball of these files under a readable manifest. The plain-text bundle
had grown past the 256 KiB that `project_read` returns inline, came back cut off, and the unpacker silently dropped
every file after the cut. The bootstrap at the top of `bundle.md` unpacks the new format; `make_bundle.py unpack`
reads both. Packed, the toolkit is about half the limit.
