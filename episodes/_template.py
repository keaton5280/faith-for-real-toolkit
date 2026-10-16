# Episode file template. Copy to episodes/S2E4.py and fill in. Plain Python, no imports.
#
# LIFECYCLE
#   Phase 1 (script day): fill EPISODE, SECTIONS, and every cue with a `beat` (the script
#            sentence it lands on) — anchors stay None. Build the cue sheet → it is the shot plan.
#   Phase 2 (transcript day): add `anchor` (verbatim transcript phrase, 6–12 words, unique) and `tc` to every
#            cue; add CORRECTIONS. check_anchors.py --fix, then --strict must pass. Render + build.
#   Phase 3 (after his edit): re-export the transcript, check_anchors.py --strict again, re-time, republish.
#
# HOUSE RULES the loader enforces or warns about:
#   one thing on screen at a time · something changes in the first minute · ceilings per 30 min: 8 dims,
#   7 ordinary AI clips + 1 hero, 8 pictures, 8 punch-ins (no minimums — a passage on her face is a choice) ·
#   a text card she doesn't read out stays under 17 characters a second (20 when she paraphrases it).

EPISODE = dict(
    code="S2E4",                       # used for filenames, the artifact title and the localStorage key
    title="Episode title",
    runtime=None,                      # "31:04" once the cut exists
    descript=dict(name="", project="", composition=""),   # fill when it is in Descript
    artifact=None,                     # the published cue sheet URL, once it exists
    lede="",                           # one or two sentences about this episode's visual approach
    # Set only when the episode has real people who were harmed in it — a crime, an abuse case, a
    # scandal, a tragedy. One line saying why. It switches on the stricter picture rules.
    sensitive=None,
    # assets_folder defaults to <PROJECT_FOLDER>\S2E4-assets — override only if this one differs.
    # A person whose reference images a clip attaches is NAMED in its prompt ("Saul, in his deep purple robe"), plus
    # whatever the scene changes; his full description lives on his card, for a clip made without the images (S2E9).
    people_in_prompts="named",
)

# (id of the first cue in the section, title, subtitle). Sections are how the cue sheet is grouped.
SECTIONS = [
    ("kinetic-open", "Open", "00:00–02:00 · what the first two minutes do"),
]

# (what she says, the correct spelling, note) — surfaced on the cue sheet for the captions.
CORRECTIONS = []

# (who, why) — the pictures the policy says no to. Listing the no makes it a decision, not an omission.
NOT_PICTURED = []

# (title, text) — callouts at the bottom of the cue sheet.
NOTES = []

# Character references — only when one person is in several clips (S2E7: Jonah in five). One image each,
# made BEFORE the clips and attached to the ones where he is big enough to recognise (refs=("jonah",) on the
# ai cue). A costume reference, not a portrait: full length, seen from behind, face hidden, plain backdrop.
# `file` defaults to ai/ref-<id>.png; `who` ("man", "woman") feeds the one sentence prepended to each clip.
REFERENCES = [
    # dict(id="jonah", name="Jonah", who="man", prompt="A character reference photograph for a film about …"),
]

CUES = [
    # ── OVERLAYS (rendered by render.py into overlays/<id>.png) ─────────────────────
    # scripture — text, ref; mode band|dim; hl="word" lights one word gold
    dict(id="scr-romans-12-15", kind="scripture", mode="dim", dur="7s",
         beat="the sentence in the script where she quotes it", anchor=None, tc=None,
         text="Rejoice with those who rejoice, weep with those who weep.", ref="Romans 12:15",
         note="★ marks a key moment; ⚠ SPELL IT marks a correction"),
    # kinetic — the words arrive one step at a time (steps are cumulative)
    dict(id="kinetic-open", kind="kinetic", dur="5s", beat="her opening list",
         steps=["First,", "First, second,", "First, second, third."]),
    # stat — hero number, sub line, optional sub2, source
    dict(id="stat-example", kind="stat", dur="6s", beat="…",
         hero="84%", sub="of Americans 13 and older listen to true crime in some form",
         sub2="about 230 million people", src="Edison Research with audiochuck"),
    # figures — up to three numbers side by side
    dict(id="stat-three", kind="figures", dur="7s", beat="…",
         rows=[("2,600+", "emailed tips"), ("2,700+", "phone tips"), ("1,000+", "digital submissions")],
         src="Moscow Police Department · by 5 December 2022"),
    # quote — text, who, optional src line (italic)
    dict(id="quote-example", kind="quote", mode="dim", dur="7s", beat="…",
         text="I was never contacted about the show.", who="Rita Isbell", src=None),
    # name — one person, lower-left, with a role line
    dict(id="name-example", kind="name", dur="5s", beat="…",
         name="Coltan Scrivner", role="Behavioral scientist. Studies morbid curiosity."),
    # names — a list of names, centred; dim for victims
    dict(id="names-example", kind="names", mode="dim", dur="8s", beat="…",
         names=["Kaylee Goncalves", "Madison Mogen", "Xana Kernodle", "Ethan Chapin"]),
    # timeline — two or three dated rows with a gap label between them
    dict(id="timeline-example", kind="timeline", dur="7s", beat="…",
         rows=[("27 December 2022", "Police say publicly that she was not involved."),
               ("30 December 2022", "The suspect is arrested.")], between="three days"),

    # ── AI CLIPS (Keaton generates, Gemini app or Flow) ─────────────────────────────
    # The default since 15 Oct 2026 is a DARING TAKE ONLY (Keaton, 13 Oct: "Only do 'daring takes' for AI video"):
    # daring=dict(image=…, video=…, refs=…, guards=…) and no image/video of its own — the shot written as cinema, faces,
    # a moving camera and hands allowed, saved as ai/<id>.mp4, three or four outputs per card. Put clips on the peaks
    # the episode builds to, not on setup. People with reference images are NAMED, not described (people_in_prompts).
    # refs name ids from REFERENCES or a standing character in characters.py ("saul-back", "jesus-front", …).
    # guards: only what this shot could actually break — "modern", "crowd", "animals", or a sentence of your own.
    # A two-shot beat: daring=dict(…, then=dict(image=…, video=…, cut_on="her word for the cut")), dur up to 20s.
    # A SAFE take (image=/video= on the cue itself, face hidden, camera still) is the per-episode exception now —
    # e.g. when Katrina hasn't seen a face clip yet. The style block and guard rail are appended on copy.
    # Bible and history scenes only. No still lifes. mode "cut" (replaces her) or "pipclip" (laid in the corner).
    dict(id="ai-example", kind="ai", mode="cut", dur="8s", priority=1, beat="…",
         title="The road to Damascus — Acts 9",
         daring=dict(refs=(), guards=("modern",),
                     image="Midday on the dusty road to Damascus in the first century AD, open country of dry hills under a "
                           "pale sky, the city walls far ahead. Low and close beside a traveller in a dusty wool cloak who "
                           "has dropped to his knees in the road, one hand thrown up against a white light pouring from "
                           "ahead; two companions stand frozen a few paces behind him. Photographed on 35mm film: ochre, "
                           "bone and slate, fine grain.",
                     video="The light ahead swells until it floods the frame as the camera pushes in on the kneeling man's "
                           "face, eyes screwed shut, mouth open; his companions stagger back and shield their eyes, and dust "
                           "lifts off the road around them."),
         note="Why this shot, which peak it sits on, and where it cuts back to her."),

    # ── PICTURES (Keaton retrieves; framing.py frames them into overlays/<id>.png) ───────
    # what, source (where to look), rights pd|art|cc|official|frame|news, credit (on-screen line),
    # search (query for the search link), aspect. Save the file as pictures/raw/<id>.jpg
    # `art` = public-domain painting/engraving/map — the workhorse for a Bible or theology episode.
    # `own` = a photograph Keaton or Katrina takes of the thing itself (S2E6: their own truck) — no search
    # link on the card, and the standing rules apply to the frame: no people, nothing that places the house.
    dict(id="pic-example", kind="picture", dur="5s", beat="her first mention of the show by name",
         what="Official key art for the series", source="The studio's media center, or the poster in the Wikipedia infobox",
         rights="official", credit="Netflix", search="series name key art poster", aspect="portrait",
         note="Why it helps the viewer, and why it is allowed."),

    # ── MAPS (Claude renders; nothing to fetch) ─────────────────────────────────────
    # places = [(name, lon, lat, label side)] — LONGITUDE FIRST. context = the same shape, for
    # places shown in grey for orientation but not on the route. mode "pip" (corner) or "full".
    # Renders as cumulative steps <id>-1.png … <id>-n.png (place like kinetic text, one city per
    # scene) AND <id>.webm (silent, transparent, travels on its own clock). motion=False skips
    # the video. Needs geo/med.json — run `python3 setup_geo.py` once.
    dict(id="map-example", kind="map", mode="pip", dur="6s", beat="the sentence where she names the places",
         places=[("Tyre", 35.203, 33.271, "ne"), ("Caesarea", 34.892, 32.500, "sw")],
         context=[("Jerusalem", 35.226, 31.778, "se")],
         credit="Acts 21:7–8 — down the coast to Caesarea",
         note="Why the geography matters here."),

    # ── PUNCH-INS (Katrina's; candidates only) ───────────────────────────────────────
    # A punch-in is two scene breaks in Descript: `anchor` is where the frame tightens and
    # `out` is where it releases. Give both, or the second break is guesswork in the edit.
    dict(id="punch-example", kind="punch", beat="the line that lands",
         anchor="verbatim phrase where the frame tightens",
         out="verbatim phrase where it goes back to the wide",
         why="Why this line earns a tighter frame."),
]
