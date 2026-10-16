#!/usr/bin/env python3
"""House style for Faith for Real episode visuals.

Everything that should stay the same from episode to episode lives here:
the frame, the palette, the type, the look of the AI clips, the picture
corner, the cue kinds and their quotas, and the list of prompt words that
seed generation failures. Episode files never restate any of this.
"""

# ── frame ──────────────────────────────────────────────────────────────
W, H = 1920, 1080

# ── where everything lives on dadtop ───────────────────────────────────
# One folder for the whole channel: the toolkit in visual-pipeline\, one <CODE>-assets\ per episode.
PROJECT_FOLDER = r"C:\Users\keato\OneDrive\Documents\Claudjects\FaithForReal"

# ── type (fetched by setup_fonts.py into fonts/) ───────────────────────
FONT_DIR = "fonts/"
GAR   = "eb-garamond-latin-500-normal.ttf"   # verse, quotes, names
GAR_R = "eb-garamond-latin-400-normal.ttf"
GAR_B = "eb-garamond-latin-600-normal.ttf"
GAR_I = "eb-garamond-latin-500-italic.ttf"
INT   = "inter-latin-500-normal.ttf"         # labels, references, sources
INT_B = "inter-latin-600-normal.ttf"

# ── palette ────────────────────────────────────────────────────────────
WARM  = (245, 239, 228)   # text — an off-white that survives over her warm set
GOLD  = (226, 170, 130)   # accent — references, names, numerals
DIM   = (232, 224, 210)   # secondary text
SCRIM = (14, 11, 9)       # the dark of every scrim
SET   = dict(wall="#7F6D4D", curtain="#C1826B", table="#95542F")  # sampled from her frame

# ── picture-in-picture corner ──────────────────────────────────────────
# Over her left shoulder = screen right: the plain olive wall between her
# hair and the curtain, above the side-table lamp. Re-measure if the set moves.
# Pictures are NOT cropped to a common aspect ratio — cropping a tall statue or a portrait
# painting to fit a landscape box destroys it. Instead every picture is scaled to the same
# AREA and centred in the same vertical band, so the shape varies but the visual weight does
# not, and the credit line always lands in the same place. max_w / max_h are clamps for the
# extremes (a panorama, a very tall statue), not the target.
# ── the mount a picture was scanned on ─────────────────────────────────
# Library and museum scans of a single object arrive on a flat white or flat black card.
# A bright card over her shoulder reads as a graphic, not as a thing, and it also eats the
# constant-area budget the object should be getting. Every picture is trimmed of a uniform
# mount by default; matte="knockout" on a cue goes further and drops the mount out to
# transparency, and matte="keep" turns both off.
MATTE = dict(tol=10,          # how far from the corner colour still counts as mount
             surround_tol=18, # matte="knockout" on a picture with a flat COLOURED surround — a 3D viewer's grey,
                              # a museum's backdrop: how far from that colour still counts as surround (S2E7)
             surround_share=0.6,  # …and how much of the outer ring has to be that colour before it is dropped
             light=246,       # a white mount is at least this bright in every channel
             dark=12,         # a black mount is at most this dark
             pad=2,           # leave a hair of it so the subject is not shaved
             max_crop=0.45,   # never take more than this fraction off any one side
             paper=(243, 237, 225))  # matte="paper": the old-book page a cut-out engraving is set back on (S2E9)

# `top` + `band_h` is the SHELF: every picture's bottom edge sits on it, whatever shape the
# picture is, and the caption sits `credit_gap` under that line. Bottom-aligned rather than
# centred in the band, because those are the two things that have to be true at once — the
# caption belongs to the picture, so it has to be tight against it, and it must not jump
# between cues. Centring the picture bought the second at the cost of the first: a wide
# picture floated a hundred pixels above its own caption. On a shelf, both hold. What moves
# instead is the TOP edge, which nobody reads as movement because there is nothing above it.
PIP = dict(side="right", area=150_000, max_w=560, max_h=470, top=84, band_h=470, margin=96,
           radius=10, border_alpha=90, credit_size=22, credit_gap=10,
           # The caption is justified to the picture's own width, so the two of them read as one
           # object rather than as a picture with a line of text near it. Justified by stretching
           # the WORD SPACES, never the letterforms — spaced-out letters are a display treatment and
           # this is sentence case. A caption too long to sit on one line at this size wraps, and the
           # break is chosen to make the lines as even as possible so neither one has to stretch far.
           # A caption is set at the largest size in this range that lets it fill the measure on
           # ONE line; only a caption too long for that even at the smallest size wraps, and a
           # wrapped one goes back to the full size because two lines have the room. The range is
           # narrow on purpose — nobody sees two captions at once, minutes apart, but everybody
           # notices one they cannot read.
           credit_size_min=17, credit_size_max=25, credit_lines_max=3, credit_leading=1.35,
           credit_space_min=0.55, credit_space_max=2.4)   # multiples of the font's own space

# ── maps ───────────────────────────────────────────────────────────────
# A map cue draws the coastline she is talking about and walks a dotted line between the places
# she names. It is framed by the picture code — same corner, same shelf, same caption — or full
# frame on the dark ground when the journey needs the width. Two outputs, because they are good
# at different things: cumulative PNG steps, which advance on HER WORDS (placed exactly like
# kinetic text), and a silent alpha WebM, which travels on its own clock under a longer passage.
# Coastline: Natural Earth 10m land, fetched and clipped once by setup_geo.py into geo/med.json.
MAP = dict(
    sea=(18, 20, 23),        # a cold slate, so the warm land and the gold route separate from it
    land=(66, 58, 48),       # her wall, darkened — the map reads as an object on the set
    coast=(138, 124, 104),
    ghost=(140, 130, 116),   # a place shown for orientation that is not on the route
    aspect=1.35,             # of the tile; the framing scales it to the standard visual weight
    pad=0.16,                # margin around the places, as a fraction of their own span
    bow=0.055,               # how much each leg curves; a straight line reads as a ruler, not a voyage
    dot_r=2.3, dot_gap=10.0, # the dotted line, at corner size
    city_r=4.4, head_r=5.4, label=18, label_gap=5,
    fps=24, hold_in=0.5, hold_out=0.8,
    # The motion file. Descript imported a VP9 WebM with alpha as a black rectangle (S2E5), so the
    # transparent format is QuickTime Animation in a .mov — lossless RGBA, decoded by everything,
    # and under 2 MB for six seconds because most of the frame is transparent. If a .mov ever comes
    # in black too, the PNG steps are the format that cannot fail and motion=False turns this off.
    # (ProRes 4444 is the other option and also works: -c:v prores_ks -profile:v 4444
    #  -pix_fmt yuva444p10le. It is ten times the size for no visible gain here.)
    motion_ext="mov", motion_args=("-c:v", "qtrle", "-pix_fmt", "argb"),
)

# ── charts ─────────────────────────────────────────────────────────────
# An org chart, drawn and revealed a rank at a time — for the sentences where she stops to explain
# who outranks whom (a tribune and his garrison, a centurion and his hundred). Same corner, same
# shelf, same caption as a picture; cumulative PNG steps, so the rank below arrives on her word for
# it. Figures are geometric on purpose: the point is a count and a chain of command, not a likeness.
CHART = dict(
    ground=(24, 22, 20),     # a warm near-black, so her set reads through the edges of the card
    rank=(176, 166, 150),    # the ranks under the officer
    subcol=(150, 141, 127),
    rule=(110, 100, 88),
    aspect=1.16,             # of the tile — a chart is taller than a map
    pad=18, cols=10,         # inner padding; figures per row in a block
    figure_big=78, figure_small=20,
    gap_x=1.5, gap_y=1.7,    # multiples of the figure height
    label=17, sub=13, label_gap=15, connector=34,
)

# ── the AI look ────────────────────────────────────────────────────────
STYLE_IMAGE = (
    "Photographic realism, as if shot on 35mm film with a 50mm lens, natural light only from a single source — dawn, dusk, a window, or fire. "
    "Muted palette of ochre, olive, bone and slate; warm shadows, soft highlights, gentle film grain. "
    "Any people are seen from behind, at a distance, or in silhouette — never a clear face, never hands at work. "
    "Period-accurate, no modern objects. Quiet, unhurried composition with room to breathe. "
    "Not painterly, not illustrated, not epic, no lens flare, no text.")

STYLE_VIDEO = (
    "Match the first frame exactly in style, lighting and colour. Nothing enters the frame that is not already in the first frame. "
    "No camera shake, no speed changes, no cuts, no text. "
    "Silent — no audio, no music, no sound effects, no dialogue, no ambience.")

# STANDING DECISION (2026-09, Keaton): every clip is written for Veo text to video. The ChatGPT
# start frame is no longer the default path — one prompt goes in and a clip comes back, which is
# fewer steps, and the frames-to-video discipline only ever existed to protect an input image.
# `frames` still accepts "start" and "start+end" for a shot that genuinely needs a fixed opening
# composition; it just is not what a new cue gets unless it asks.
CLIP_FRAMES_DEFAULT = "none"

# ── character references (added for S2E7, Jonah) ──────────────────────
# When one person appears in several clips, a single reference image keeps him the same man from clip to
# clip. A reference is NOT a start frame: Flow's Ingredients mode (Veo 3.1) and the Gemini app (Gemini Omni,
# which replaced Veo there in 2026) take reference images that fix what a character looks like without
# fixing the composition, whereas a start frame fixes the whole first frame — which is where the driverless
# cart came from. So the standing text-to-video decision holds; a reference is only an attachment to it.
# On this channel it is a COSTUME reference, never a portrait. Clips never show a face, so what has to match
# is the clothes, their colours, the build and the silhouette — and a reference with a clear face invites the
# model to turn him round and show it. Full length, three-quarter view from behind, face turned away, plain backdrop.
# Declare it in the episode's REFERENCES and give each clip that uses it refs=("<id>",). Only the clips where
# he is big enough to recognise get it; a figure that is a speck or a silhouette does not need it, and the
# reference tends to pull the camera toward the character. Up to S2E8 every prompt of him also described him in
# the same words, so a clip with a reference worked as plain text to video with its first sentence deleted. From
# S2E9 (EPISODE people_in_prompts="named") the prompt only names him and his description sits on his card instead.
REF_LEAD = ("The {who} in the reference {img} is {name}: keep the clothes, their colours and the build exactly as "
            "they are in {them}, but not {its} {pose}, {its} plain backdrop or {its} framing.")

# Said once, ahead of the lead, on every card that attaches a reference (added for S2E7). The Gemini app took Jonah's
# photographic front view for a real person and refused the clip: "I can't make videos of real people in situations
# like that." It is true of every reference on this channel — each one is generated, never a photograph of anyone — so
# the card says so up front instead of Keaton having to argue it in the chat afterwards.
REF_INTRO = {1: "The reference image is an AI-generated character design, not a photograph of a real person.",
             2: "The reference images are AI-generated character designs, not photographs of a real person."}

# ── daring takes (added for S2E7, at Keaton's request) ─────────────────
# Every ai cue can carry a second, bolder prompt in daring=dict(image=…, video=…, refs=…, guards=…): the same beat,
# shot the way a film would shoot it — the face on screen, the camera moving, the fish in frame, hands doing things —
# saved as ai/<id>-daring.mp4 beside the safe take. The safe take is the one the house rules were written for and it
# stays on the card unchanged; the daring take is an experiment against those rules, and the editor keeps whichever
# of the two came out better. With a front-facing reference it also asks the model to hold his face steady, which is
# the whole reason a face reference exists.
REF_LEAD_DARING = ("The {who} in the reference {img} is {name}: keep {poss} face and hair, the clothes, their colours and "
                   "the build exactly as they are in {them}, but not {its} {pose}, {its} plain backdrop or {its} framing.")

STYLE_VIDEO_DARING = (
    "One continuous take, no cuts. Photographic realism, as if shot on 35mm film — not illustration, not a render. "
    "No on-screen text, captions, subtitles or watermarks. "
    "Silent — no audio, no music, no sound effects, no dialogue, no ambience.")

DARING = dict(
    lifted=[
        "Faces — medium shots and close-ups, and an actual performance: fear, relief, fury",
        "Camera moves — handheld, dolly, tracking, crane, orbit, rack focus",
        "Animals — on screen, not implied",
        "Hands doing things — a hand on a shoulder, a finger running along a scroll, a man pushing himself up",
        "Speed and force — a man running flat out, a storm at full strength, a shape surging up out of the deep",
        "Several motions in one clip, and the full length the model hands back",
    ],
    held=[
        "No on-screen text",
        "Silent — her narration runs under every clip",
        "Nothing modern",
        "Photographic realism in the house look — the same film, the same palette",
    ],
    # Not the house's rules but the generator's (S2E7): the Gemini app refused Jonah thrown overboard twice — first as
    # "real people in situations like that" (the face reference), then, told he was AI-generated, as "dangerous
    # situations". lint_prompts.py flags the trigger words; `then=dict(…)` on a daring take is the way round it.
    refused=[
        "A recognisable person in mortal danger — thrown, drowning, sinking, swallowed, flung. With a face reference "
        "attached the Gemini app reads him as a real person and refuses; without one it can still call the shot a "
        "dangerous situation",
        "So the dangerous moment happens in the cut: the moment before, with his face, and the moment after, without "
        "him — a daring take in two shots, then=dict(…), as S2E7's overboard is",
        "Arguing in the chat changes nothing — the chat agrees, the filter does not. Start a new chat for each try",
    ],
    note=("The face rule is recorded in the guard table as Katrina's, and the daring takes break it on purpose, as an "
          "experiment. Let her see a face clip before one goes into an episode. Expect more failures per generation — "
          "faces that drift between frames, a fish that turns into a monster, hands with the wrong number of fingers — "
          "and take three or four outputs per card rather than two."),
)

# Text to video — frames="none". A different craft, not the same one with the picture removed.
# The negative-heavy discipline above exists to stop a model contaminating a start frame it was
# handed; with no start frame there is nothing to protect, and the same prompt style just produces
# empty, static, lifeless shots. Here you describe the shot you want in positive cinematic language
# and let it move. Only the channel's own rules stay, and they are stated once.
STYLE_VIDEO_NOFRAME = (
    "One continuous take, no cuts. No camera move beyond a slow push of a few percent. "
    "Photographic realism, as if shot on 35mm film — not illustration, not a render. "
    "No on-screen text, captions, subtitles or watermarks. "
    "Silent — no audio, no music, no sound effects, no dialogue, no ambience.")

# The rules that are NOT universal, appended per cue with guards=("faces", "modern", ...).
# An entry is either one of the keys below or a sentence of your own, for a shot whose particular
# temptation is not on this list — the point is that every line appended to a prompt should be
# something that shot could actually get wrong.
# A guard the shot cannot break is noise in the prompt: it spends the model's attention and it
# tells it to think about something that was never in the scene. "Never a depiction of Jesus" on an
# empty shoreline is the clearest case — nothing in that prompt was going to put him there. And a
# guard has to be CONCRETE to mean anything: "period-accurate" says nothing unless the prompt
# itself names the century and the place, so the period belongs in the shot description, and what
# goes here is only the specific modern things that would otherwise creep into THIS shot.
GUARD_LINES = dict(
    faces=("Everyone in frame is seen from behind, at a distance, or in silhouette — no face is "
           "resolved at any point."),
    christ=("No figure of Jesus appears anywhere in the shot: the light, the reaction and the "
            "aftermath only."),
    modern=("Nothing modern anywhere in frame — no electric light, no vehicles, no modern boats, "
            "buildings, clothing, signage or road markings."),
    hands="No hands doing close work, writing, or handling small objects.",
    animals="No animals in frame.",
    crowd="At most a handful of people near the camera; any larger group stays far back and small.",
)

# What seeds a bad generation, what it looks like, and the rule that avoids it.
# The linter (lint_prompts.py) enforces the mechanical ones; the cue sheet and the
# skill show the whole table so a new prompt is written under it, not fixed after.
GUARDS = [
    ("A motion prompt that introduces anything not in the start frame",
     "The model has to invent it mid-clip — that is the driverless cart.",
     "Every noun in the video prompt is already in the image prompt. The linter checks this."),
    ("Hands doing anything",
     "Extra fingers, pens that pass through the page, scrolls that melt.",
     "Objects only, or hands at rest and out of focus. Never writing, never handling small things."),
    ("A face",
     "Uncanny, morphing, wrong-eyed — and it breaks her rule about faces.",
     "Backs, distance, silhouettes. Never a clear face on a safe take — Jesus included, when he is in the shot."),
    ("Legible text",
     "Gibberish glyphs that pull the eye.",
     "Scrolls rolled, turned away, or out of focus; say 'no legible text' in the image prompt."),
    ("Crowds",
     "Merging bodies, duplicated people, the same face twice.",
     "At most four people near camera; a crowd only far back and small, seen from behind."),
    ("Animals and vehicles",
     "Extra legs, gaits that slide, carts with nothing pulling them.",
     "Leave them out. If a scene needs one, it is static, distant, and in the start frame."),
    ("'Lightning bolt'",
     "A cartoon zigzag.",
     "'A light pulses from inside the cloud — a glow, not a drawn bolt.'"),
    ("Camera moves",
     "Warping architecture, ground that swims.",
     "Locked off, or a push-in of a few percent. Never pan, orbit, dolly, handheld."),
    ("Speed words — suddenly, quickly, rushes",
     "Smearing and frames that morph.",
     "One slow motion per clip. 'Unhurried.' Four to six seconds."),
    ("Two motions in one prompt",
     "The model picks one, or blends both.",
     "Name the one thing that moves, then what stays still, then close with what must not appear."),
    ("An end frame that changes the composition",
     "A morph between two stills.",
     "End frame only when the shot arrives somewhere (Damascus → white). Same camera; change only light or position."),
    ("A subject cropped at the frame edge",
     "New geometry grows in from the edge.",
     "Anything that will move sits fully inside the frame with margin."),
    ("Modern objects",
     "Watches, glasses, zippers, plastic bottles.",
     "Name the period in the shot itself — the century, the materials, what people are wearing. "
     "A prompt that only says 'period-accurate' has told the model nothing, and with a start frame, "
     "check it for watches and zippers before animating anything."),
    ("Frames-to-video discipline carried into a text-to-video prompt",
     "Flat, empty, static shots — everything you told it not to do, and nothing you wanted.",
     "The pile of negatives protects a start frame from contamination. With no start frame there is nothing "
     "to protect and they only suppress motion. Describe the shot in positive cinematic language — subject, "
     "action, camera, light — and keep only the channel's rules. Use STYLE_VIDEO_NOFRAME, not STYLE_VIDEO."),
    ("A shadow, reflection or silhouette that has to change shape on its own",
     "Frozen shadows that ignore the prompt, or people growing into frame to cast them, or shapes that melt. "
     "Taking the bodies out does not make it easier — it makes it impossible.",
     "A shadow only changes because the light changed. If a shape has to change, the thing making the shape is "
     "in the start frame. Same for an overhead or top-down camera: safe when nothing has to move, unreliable the "
     "moment something does."),
    ("Leaving audio on",
     "The model scores the clip — music, wind, crowd noise, invented voices — and it fights her narration under the cut.",
     "Every clip is silent. The guard rail appended to every video prompt now ends with 'Silent — no audio…'. "
     "If a generation still comes back with sound, mute that layer in Descript before you place it."),
]

# Placing a clip: "cut" replaces her for a few seconds; "pipclip" lays it over her and resizes it into
# the corner (Keaton does this by hand in the editor, and it is why a corner video needs no alpha —
# he scaled two Gemini-made map clips into the corner for S2E5 rather than using the rendered steps or
# the transparent .mov). A clip that explains something belongs in the corner; a clip that IS the scene
# replaces the frame.

# ── the hero clip ──────────────────────────────────────────────────────
# One AI clip per episode may be the hero: the shot worth spending real money and real
# iteration time on. The guard table above is calibrated to what video models reliably
# fail at, and models improve — so on the hero clip the guards that exist because the
# MODEL could not do the thing are lifted, and the guards that exist because of what the
# CHANNEL will not show are not, ever. Mark it with hero=True on the ai cue. The loader
# allows exactly one and leaves it out of the ordinary clip quota, because it is a
# deliberate extra spend rather than one of the four-to-seven.
HERO_CLIP = dict(
    per_episode=1,
    lifted=[
        "Crowds — many figures moving at once, which is the improvement current models actually claim",
        "Fluid dynamics — water, fire, smoke, rain, dust at scale",
        "More than one motion in a single prompt",
        "The full eight seconds, rather than the four-to-six that kept earlier models from drifting",
    ],
    held=[
        "A clear face, ever",
        "Hands doing fine work",
        "Legible text",
        "Modern objects in a period scene",
        "Animals — the gait problem is not one anybody claims to have fixed",
        "Camera moves beyond a few percent push-in",
    ],
    note=("Everything held is either her rule or a failure nobody has claimed to fix. When a model "
          "release claims one of them, move the line here — do not quietly break it on an episode."),
)


# ── cue kinds ──────────────────────────────────────────────────────────
# kind → (label, hue, default mode)
KINDS = {
    "scripture": ("Scripture", "#6E7350", "band"),
    "stat":      ("Stat",      "#52687E", "band"),
    "figures":   ("Stat",      "#52687E", "band"),
    "quote":     ("Quote",     "#A8624A", "dim"),
    "name":      ("Name",      "#7A6A5C", "band"),
    "names":     ("Name",      "#7A6A5C", "band"),
    "timeline":  ("Explainer", "#52687E", "band"),
    "kinetic":   ("Scripture", "#6E7350", "band"),
    "ai":        ("AI clip",   "#6B5E80", "cut"),
    "picture":   ("Picture",   "#4F7068", "pip"),
    "map":       ("Map",       "#4F7068", "pip"),
    "chart":     ("Chart",     "#52687E", "pip"),
    "punch":     ("Punch-in",  "#8C8D85", "punch"),
}
OVERLAY_KINDS = ("scripture", "stat", "figures", "quote", "name", "names", "timeline", "kinetic")
CHIP_ORDER = ["scripture", "stat", "quote", "name", "timeline", "ai", "picture", "map", "chart", "punch"]
CHIP_MERGE = {"figures": "stat", "names": "name", "kinetic": "scripture"}

MODES = {
    "band":  "A soft dark scrim rises from the bottom edge; text sits in the lower third. Drop it on top of her, fade in 0.6 s, fade out the same. Nothing about her layer changes.",
    "dim":   "The scrim covers the whole frame at about 45% and the text is centred. Her footage stays live underneath. Pivot moments only — eight in a half hour is the ceiling.",
    "cut":   "A generated clip replaces her for four to six seconds, then cuts straight back. No stock footage, no still lifes.",
    "pip":   "A picture over her left shoulder — screen right, on the plain wall — for four to six seconds, faded in and out. Never at the same time as anything else.",
    "full":  "The picture fills the frame and replaces her, cut in and out like a generated clip. For the two or three pictures an episode that are worth actually looking at rather than glancing at over her shoulder — a painting with something in it you want the audience to find. Can carry an arrow.",
    "map":   "A map of the places she is naming, with a dotted line that travels between them. Two files ship for every map: numbered PNG steps, placed exactly like kinetic text so the line reaches each city on her word for it, and a silent motion file that travels on its own — a .mov with a transparent background for a corner map, an ordinary .mp4 for a full-frame one. Use the steps when she names the places in one sentence, the motion file under a longer passage. Corner or full frame, never both at once with anything else.",
    "chart": "An org chart in the picture corner, revealed a rank at a time: the officer is on screen while she names him, and the rank under him arrives on the word for it. Numbered PNGs, one per rank, placed exactly like kinetic text — scene break, drop, six-frame cross-fade to the next.",
    "pipclip": "A generated clip laid OVER her footage and resized down into the corner, rather than replacing the frame. Keaton's method, and it needs no alpha channel and no toolkit rendering — an ordinary opaque video, scaled and positioned once in the editor. Use it for anything explanatory that moves: a map, a diagram, a process, a scene that belongs beside her rather than instead of her.",
    "strip": "A very wide picture laid across the bottom of the frame, over her, with her face still in shot above it — a frieze or a panorama that the corner would shrink to a sliver. Four to six seconds, faded in and out, like a picture in the corner.",
    "punch": "Katrina's. A hard cut to a tighter framing of her on a line that lands, back out on the next thought. Never during a cut, picture or dim. In Descript it is two scene breaks — one where the frame tightens and one where it releases — so a punch cue carries two anchors, not one.",
}

DEFAULT_DUR = {"map": "6s", "chart": "7s", "scripture": "6s", "stat": "6s", "figures": "7s", "quote": "6s", "name": "5s",
               "names": "6s", "timeline": "7s", "kinetic": "5s", "ai": "5s", "picture": "5s", "punch": "—"}

# per ~30 minutes; the loader warns above the upper number. Since 15 Oct 2026 nothing warns BELOW one: a clip or a
# picture goes where a moment calls for it, and a passage that stays on her face is a decision, not a gap. The one floor
# kept is the first minute (FIRST_MINUTE), because that is where the 2 Oct review found 46–60% of viewers gone.
QUOTAS = dict(ai=(4, 7), picture=(3, 8), dim=8, punch=(4, 8), total_per_minute=(1.0, 2.0))
FIRST_MINUTE = 60

# ── reading load (added 15 Oct 2026) ─────────────────────────────────────
# A text card has to be read while she keeps talking. Characters a second a viewer can take in: the usual ceiling for
# adult subtitles is 17–20. `cps` (17) applies when she is saying something else; `cps_paraphrase` (20) when she
# paraphrases the card (at least `paraphrase` of its longer words are in her sentence); a card she reads out
# (`along` or more) is exempt, because the eye follows the ear. `verse_min_px`: below this the fitter has shrunk a long
# verse past what an upright phone shows legibly (about 11 pt); render.py warns. Measured on S2E3–S2E9: the 23 verse
# cards over 17 a second were also the smallest type (median 68 px against 88).
READ = dict(cps=17, cps_paraphrase=20, paraphrase=0.4, along=0.6, verse_min_px=56)

# ── spacing: one thing on screen at a time ─────────────────────────────
# A punch-in has no duration of its own, so assume this much frame time for it
# when checking whether it collides with the overlay on either side.
PUNCH_DUR = 3
# What the video model actually hands back, whatever length the cue asked for. Veo returns
# eight seconds every time, so `dur` on an ai cue is SCREEN TIME — how long it should be on
# screen once trimmed — and never an instruction to the generator. Spacing is checked against
# this, not against `dur`, so an untrimmed clip dropped straight onto the timeline can never
# collide with the cue after it.
CLIP_DELIVERED = 8
# Daylight between one visual clearing and the next arriving. Under this and the
# two read as one continuous graphic, which is the thing the whole format avoids.
BREATH = 2

# ── pictures: where one may come from ──────────────────────────────────
# key → (label, status, guidance); status is ok | avoid | never.
# An editorial risk policy, not legal advice.
RIGHTS = {
    "pd":       ("Public domain / government", "ok",
                 "Expired copyrights, US federal works, official releases, Wikimedia Commons public-domain files. Credit the source anyway."),
    "art":      ("Public-domain artwork", "ok",
                 "A painting, engraving, fresco, illumination or map old enough to be out of copyright — Commons has the high-resolution scans. The most useful class for the biblical and theology pillars: it can show a face and a scene where a generated clip cannot, and it reads as history rather than as a render. Credit artist, title and date."),
    "cc":       ("Creative Commons", "ok",
                 "Wikimedia Commons and Flickr CC files — most photographs of real places live here. Credit exactly as the licence asks: photographer, licence name."),
    "official": ("Official material", "ok",
                 "Cover art, key art, a logo, a product screenshot, a press-kit portrait or still for the thing she is discussing — shown small and briefly while she discusses that thing, credited to the rights holder. Commentary is the strongest fair-use footing there is; decoration is the weakest."),
    "frame":    ("A frame of the work itself", "ok",
                 "A still or screenshot from the film, series, video or app under discussion. Same conditions as official material, five seconds or less, credited."),
    # Added for S2E6, where the thing under discussion was the family's own truck: the only honest
    # picture of it is one Keaton takes, and the card must not send him to an image search for it.
    "own":      ("Your own photograph", "ok",
                 "A photograph Keaton or Katrina takes of the thing she is discussing — their truck, their workbench, their "
                 "front door. Nothing to license and nobody to credit, so the credit line is purely a caption. The standing "
                 "rules still apply to what is in the frame: no people, and nothing that places the house — no plate, no "
                 "house number, no street sign. The card has no search link, because a stranger's photograph of the same "
                 "model is not a picture of this one."),
    "gen":      ("Generated reconstruction", "label",
                 "A still made by an image model showing a real place as it may have looked, rather than a "
                 "photograph of what is there now. Nothing to license and nobody to credit — the cost is "
                 "different and it is a credibility cost. The whole reason a picture beats a clip on this "
                 "channel is that a picture is EVIDENCE: a real object, a real site, a real painting somebody "
                 "made at the time. A reconstruction is an illustration wearing a photograph's clothes, and a "
                 "caption reading 'The forum at Philippi' over one is a claim that is not true. So this class "
                 "is allowed, and it is allowed on one condition, which the loader enforces: the credit line "
                 "says the word reconstruction. Then it is honest, and it can be genuinely better than the "
                 "photograph — a first-century harbour explains the beat where a field of rubble does not."),
    "news":     ("News-agency photograph", "avoid",
                 "AP, Getty, Reuters, pool footage. Agencies do issue claims. If it is truly the only image, three seconds, credited, and expect the possibility of a takedown — and first ask whether the name overlay already does the job."),
    "no":       ("Ruled out", "never",
                 "Recorded in NOT_PICTURED with the reason instead of being placed."),
}

# Subjects, in plain words, for the page and the skill.
# `no` is the standing rule for every episode. `sensitive` applies on top of it only when the
# episode has real people who were harmed in it — set EPISODE["sensitive"] to say why.
# The test that comes before the rights question, and the one that is easiest to fail:
# WHEN THIS IS ON SCREEN, DOES THE VIEWER KNOW WHAT THEY ARE LOOKING AT?
# They get five seconds and no second chance. It is answered by the audio naming the thing while
# it is up, or by the credit line saying what it is in a glance. If neither does it, the picture
# is not context — it is a puzzle the viewer solves instead of listening, and it costs more than
# the empty corner would have. Cut it rather than hope.
#
# That makes the on-screen credit a CAPTION first and an attribution second: "Papyrus 46 — the
# oldest copy of Paul's letters, c. AD 200", not "University of Michigan Library". Licence
# attribution — photographer, licence name, link — goes in the video description, which is the
# normal and accepted way to attribute CC material in a video.
SAYS_WHAT_IT_IS = ("The audio names it while it is up, or the credit line identifies it in a glance. "
                   "If neither, cut the picture.")

# The other half of the same test, from Keaton on S2E6: a caption is for what the eye cannot supply.
# When the picture already says what it is — rust on a truck, the truck she is talking about — the
# credit line stays EMPTY and nothing is printed under the picture. Captions are for the things a
# viewer cannot tell by looking: what a manuscript is, who painted a painting and when, where a
# place is. Spelling out what is plainly in the frame reads as filler.
CAPTION_RULE = ("And a picture that already says what it is gets no caption at all — rust on a truck is "
                "rust on a truck.")

PICTURE_POLICY = dict(
    yes=["The thing she is discussing — a book cover, an album or podcast tile, key art, a logo, an app screen, a study's title page",
         "A real place — a city, a ruin, an excavation, a church, a campus, a building — photographed",
         "A public figure in a public role — an author, a researcher, a theologian, an official — in an official or press portrait",
         "An object or document — a manuscript page, an inscription, an artifact in a museum, a map, a product",
         "Public-domain artwork of the scene or figure she is describing — the workhorse for a Bible or theology episode",
         "A diagram Claude can draw, when the point is a shape or a comparison rather than a photograph"],
    no=["A private individual — anyone who did not seek public attention — identified by photograph",
        "Anyone in distress, grief, crisis or a medical setting",
        "Children, other than incidental and unidentifiable, and never named",
        "Family or social-media photographs of anyone, public figures included",
        "A real person's photograph used to illustrate a negative generalisation about a group",
        "Anything watermarked, screenshotted from a paywall, or of unknown origin"],
    sensitive=["Victims, living or dead — names as text only",
               "Victims' families in grief or testimony",
               "Crime-scene, evidence, memorial or funeral imagery",
               "Anyone accused but not charged, or a defendant outside official imagery — a booking or court photograph only",
               "Any styling borrowed from the genre being examined — red string, mugshot walls, tape"],
)

# ── full-frame pictures and arrows ─────────────────────────────────────
# A picture in the corner is a glance. Occasionally one is worth the whole frame — a painting
# with a detail the audience would otherwise never find. Those get mode="full", and can carry
# an arrow: the cue renders as two files, the picture and the picture with the arrow on it, so
# the annotation arrives on the sentence that earns it instead of sitting there from the start.
# ── a picture across the bottom of the frame (added for S2E7) ─────────
# For a picture far wider than it is tall — a frieze, a panorama, a relief that runs along a palace wall —
# the corner shrinks it to a sliver and full frame leaves most of the screen dark. Laid across the bottom of
# the frame instead, it reads at a useful size while her face stays in shot above it. Keaton's idea, for the
# Ashurnasirpal reliefs (S2E7, 4.7 to 1). The width is the frame less two margins and the height follows the
# shape; a picture that would come out taller than max_h is scaled down and centred instead, so the mode
# suits pictures about four times as wide as they are tall, or wider. The caption sits under the picture,
# flush with its left edge, like a museum label; `bottom` keeps it clear of the player controls.
STRIP = dict(margin=64, bottom=58, max_h=400, radius=8, border_alpha=90,
             shadow_alpha=175, shadow_blur=22, shadow_off=10,
             credit_size=24, credit_gap=12)

FULL = dict(
    ground=(12, 10, 8),      # the surround, for artwork that does not fill 16:9
    margin=54,               # breathing room inside the frame
    credit_size=24,
    credit_gap=12,           # the caption's own line under the picture — never on top of it (S2E7)
    arrow=dict(colour=GOLD, width=9, head=42, gap=0.022, length=0.24,
               label_size=27, label_track=5.5),
)

# Jesus may be depicted. In public-domain art, settled 2026-09-24 on S2E6 (Keaton: "Depictions of Jesus are
# fine"). In generated clips too — Keaton, 2026-10-07: "I never banned depictions of Jesus. If it makes sense
# for the story, which often is about Jesus, it's okay to depict him." Earlier toolkit versions read the first
# answer as covering paintings only and kept a clip ban that nobody had asked for; it is gone. In a clip he is a
# recurring character like Peter or Jonah: he gets reference images (an episode's REFERENCES, ids "jesus-…"),
# attached to every clip he is in, so he is the same man in every episode, and the safe-take face rule applies
# to him as to anyone. The `christ` guard stays for a shot written to keep him out of frame (the camera where he
# stands, the light and the reaction only) — a choice for that shot, not a channel rule.
DEPICT_CHRIST_IN_ART = True
DEPICT_CHRIST_IN_CLIPS = True
