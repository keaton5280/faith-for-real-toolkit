"""Standing characters — people who recur across episodes, with reference images made ONCE and reused in every one.

An episode's own REFERENCES are for someone who belongs to that episode (S2E7's Jonah, S2E8's Peter). A standing
character is different: his images already exist on dadtop and every episode attaches the same files, so he is the
same man in every clip the channel ever makes. An episode does not declare him — a clip that names one of his reference
ids in refs=(…), or in its daring take, gets it automatically (episode.py resolves it), and the cue sheet shows it as
already made, with the folder it lives in and his description.

Named, not described (S2E9, Keaton: "Why do I include character models in the Gemini prompts if you're just going to
describe the characters in the prompt as well?"). The images carry his look; the words only have to say who is who and
what this scene changes. So with his images attached a prompt calls him by name in a few words ("Saul, in his deep
purple robe") plus whatever the scene does to him (a borrowed cloak, a torn hem), and `description` is the fallback
for a clip made WITHOUT the images — on his card, pasted in place of the lead sentences. Pasted in full alongside the
images it was mostly repetition, and wherever the words and the pictures disagreed it gave the model two answers.

Jesus (made 2026-10-07): Keaton never banned depicting him — "If it makes sense for the story, which often is about
Jesus, it's okay to depict him." He chose the design from a lineup of four options, had ChatGPT make the five views, and saved
them with ChatGPT's own description in Jesus_Character_Design.
Which to attach: a safe take (face hidden) gets jesus-back alone; a daring take gets jesus-front and jesus-back, plus
jesus-face where his face is the shot. Flow's Ingredients takes three images; the Gemini app takes five, which is where
jesus-profile and jesus-full-front come in. In a clip with Peter as well, give the slots to whoever is closest to the
camera, and describe the other in words.

Saul and Samuel (added for S2E9, made 2026-10-13): the same recipe as Jesus. `design` keeps the two ChatGPT prompts
that made them — a lineup of four to choose the man from, then his five views in the same chat — so a lost set can be
remade. Keaton saved the five views but no paragraph, so their `description` was written from the saved images the
same evening and saved beside them as <Name>_Character_Description.txt. A character not made yet has made=None,
description=None and file names set in advance (view_refs), so the clip cards can already say what to attach and his
card carries the two prompts instead of a description.

`tag` is how a sentence tells two people apart when both are attached to one clip (S2E9: Saul and Samuel at Endor and
at Gilgal) — "the man in the reference images" would fit either of them, so the lead names each by what he looks like.
"""

# The frame every lineup shares, so two characters chosen from two lineups were photographed the same way.
LINEUP_FRAME = (
    "Make one wide image (3:2): a casting lineup of four different men standing side by side on a plain warm-grey studio "
    "backdrop, each shown full length in a relaxed three-quarter stance toward the camera, all lit the same way by soft, "
    "even daylight from one side. Photographic realism, like a production still from a period film shot on 35mm: natural "
    "skin texture, fine grain, muted natural colour. Not a painting, not a render. No text, numbers or labels; I'll call "
    "them 1 to 4 from left to right.")


def views_prompt(keep, face, no):
    """The second prompt, for the same ChatGPT chat as the lineup: the five views the toolkit attaches, then the paragraph.
    The same five as Jesus's set, so every standing character has the same ids and the same uses."""
    return (
        "I'm going with number __. Now make his reference set: the images I'll attach to video prompts so he is the same "
        "man in every clip. Keep everything about him exactly as in the lineup: face, hair, beard, skin, build, height and "
        f"every detail of the costume, {keep} included. Same plain warm-grey backdrop, same soft daylight from one side, "
        f"50mm lens at chest height, photographic realism like 35mm film, fine grain. No props, no scenery, no text, {no}.\n\n"
        "Make each of these as its own separate image, one at a time:\n"
        "1. Full length from behind, turned slightly to his left (a three-quarter rear view), face turned away and hidden. "
        "Portrait, 2:3.\n"
        "2. Full length, three-quarter front view, looking just past the camera. Portrait, 2:3.\n"
        f"3. Head and shoulders, three-quarter front view, {face}, both eyes visible. 4:5.\n"
        "4. Head and shoulders in profile, facing left. 4:5.\n"
        "5. Full length, straight-on front view, arms relaxed at his sides. Portrait, 2:3.\n\n"
        "After the last image, write one paragraph describing him and his costume in plain, concrete words (face, hair, "
        "beard, skin, build, each garment and its colour) that I can paste into a video prompt when I make a clip "
        "without the images, so it still matches.")


def view_refs(prefix, files=None):
    """The five views. Before they are made the file names are set in advance (<prefix>-back.png and so on); once they
    are, `files` is the names ChatGPT gave them, in the order of views_prompt — back, front, face, profile, full front
    (ChatGPT numbers them -1 to -5 in that order)."""
    files = files or [f"{prefix}-{v}.png" for v in ("back", "front", "face", "profile", "full-front")]
    return [
        dict(id=f"{prefix}-back", file=files[0],
             view="full length from behind, a three-quarter rear view; his face is turned away and hidden",
             use="Every clip he is in."),
        dict(id=f"{prefix}-front", file=files[1],
             view="full length, three-quarter front view, face visible",
             use="Every daring take he is in, always with the view from behind."),
        dict(id=f"{prefix}-face", file=files[2],
             view="head and shoulders, three-quarter front view — the face",
             use="Daring takes where his face is the shot."),
        dict(id=f"{prefix}-profile", file=files[3],
             view="head and shoulders in profile, facing left — the face in profile",
             use="The Gemini app, which takes five references."),
        dict(id=f"{prefix}-full-front", file=files[4],
             view="full length, straight front view, face visible",
             use="The Gemini app, which takes five references."),
    ]


CHARACTERS = {
    "jesus": dict(
        name="Jesus",
        who="man",
        poss="his",
        folder="Jesus_Character_Design",          # under PROJECT_FOLDER on dadtop
        made="2026-10-07",
        tag="man in the oatmeal tunic and cream mantle",
        # Verbatim from Jesus_Character_Description.txt. The fallback for a clip made without his images; with them
        # attached, a prompt calls him by name and says only what the scene changes (top of this file).
        description=(
            "Jesus is a man of about thirty with broad shoulders, a solid, lean build, a narrow waist and strong "
            "forearms. He has sun-tanned olive skin, an angular face, pronounced cheekbones, a square jaw, a strong "
            "straight nose, thick dark eyebrows and brown eyes. His dark-brown hair falls in loose waves to the base of "
            "his neck, parted slightly off-center and swept back from his forehead. He has a short, full dark beard and "
            "connected moustache, natural forehead lines and a calm, attentive expression. He wears a calf-length tunic "
            "of coarse undyed oatmeal wool, with loose sleeves ending near the elbows, lightly frayed edges, a round "
            "neckline with a short central slit, and two closely spaced dark-brown stripes running from his right "
            "shoulder to the hem. A plain oatmeal cloth belt gathers the tunic at his waist. A cream wool mantle hangs "
            "over his left shoulder, with cream tassels at its corners, each including a blue thread. His worn brown "
            "leather sandals have open toes, crossing foot straps and narrow ties around the ankles."),
        # `view` is what the picture shows; episode.py reads it the way it reads a reference prompt, to tell a view
        # that shows the face from one that hides it.
        refs=[
            dict(id="jesus-back", file="Three-quarter rear portrait of a wool-clad man-1.png",
                 view="full length from behind, a three-quarter rear view; his face is turned away and hidden",
                 use="Safe takes, and every daring take he is in."),
            dict(id="jesus-front", file="Three-quarter portrait in an oatmeal tunic-2.png",
                 view="full length, three-quarter front view, face visible",
                 use="Daring takes, always with the view from behind."),
            dict(id="jesus-face", file="Bearded Man in Oatmeal Wool-3.png",
                 view="head and shoulders, three-quarter front view — the face",
                 use="Daring takes where his face is the shot."),
            dict(id="jesus-profile", file="Bearded man in left-facing profile-4.png",
                 view="head and shoulders in profile, facing left — the face in profile",
                 use="The Gemini app, which takes five references."),
            dict(id="jesus-full-front", file="Bearded man in wool tunic and sandals.png",
                 view="full length, straight front view, face visible",
                 use="The Gemini app, which takes five references."),
        ],
    ),

    # ── Saul (added for S2E9) ───────────────────────────────────────────────────────────────────────────────────────
    # Late in his reign — Endor and Gilboa — because that is where most of his stories sit, and the stretch an episode is
    # likeliest to come back to (David, the spear, the cave). Deep purple because it reads as a king at a glance and is
    # nobody else's colour: Jonah is rust-red, Peter indigo, Jesus oatmeal and cream (the period's own association is
    # "purple garments worn by the kings of Midian", Judges 8:26). The gold band is 2 Samuel 1:10's armlet. No crown in
    # the reference, so a clip can add one or, at Endor, leave him disguised.
    "saul": dict(
        name="Saul",
        who="man",
        poss="his",
        folder="Saul_Character_Design",
        made="2026-10-13",            # the five views, saved in Saul_Character_Design; the costume came out as designed
        # Written from the five saved views (no paragraph came back with them); saved beside them as
        # Saul_Character_Description.txt. The fallback for a clip made without his images.
        description=(
            "Saul is a very tall, long-limbed man in his mid-fifties with weathered olive skin, a strong brow, deep "
            "forehead lines and a diagonal scar high on the right side of his forehead. He has dark brown eyes under "
            "heavy dark eyebrows, thick dark curly hair going grey at the temples that falls to his shoulders, and a full "
            "beard, dark at the cheeks and grey at the chin. His expression is guarded and intense. He wears a "
            "long-sleeved, ankle-length tunic of coarse cream wool. Over it a heavy deep purple wool robe hangs open from "
            "his shoulders like a long sleeveless coat, falling to mid-shin, with a dark blue tassel at each corner. A "
            "wide belt of dark tooled leather gathers the tunic at his waist, and a broad engraved gold band circles his "
            "upper right arm. He wears worn brown leather sandals with crossing straps. No crown."),
        tag="very tall man in the deep purple robe",
        design=dict(
            lineup=(
                "I'm designing the on-screen look of King Saul for a series of photorealistic short Bible films made with "
                "AI video tools. I need one character design I can reuse in every clip he is in, so first I want options "
                "to choose from.\n\n"
                + LINEUP_FRAME + "\n\n"
                "Each one is Saul, the first king of Israel, as he could have looked late in his reign, around 1010 BC: a "
                "Benjaminite farmer's son turned soldier-king, in his mid-fifties. The Bible calls him the most handsome "
                "man in Israel and taller than anyone from the shoulders up, so all four are very tall and long-limbed, "
                "with weathered olive skin, dark eyes, dark hair going grey that reaches the shoulders, and a full beard "
                "going grey. A face that was once striking and now carries years of war and strain. Each is an original "
                "face, not modelled on any actor or famous painting. No crown.\n\n"
                "All four wear the same costume, so the choice is about the man: a long-sleeved, ankle-length tunic of "
                "fine cream wool; over it a heavy wool robe dyed deep purple, open down the front and falling to "
                "mid-shin, with a tassel at each of its four corners (each tassel with a single blue thread); a wide belt "
                "of dark tooled leather; a broad, plain gold band on his upper right arm; worn leather sandals.\n\n"
                "Make the four men clearly different:\n"
                "1. A long, lean, hollow-cheeked face; a high-bridged nose; straight hair; a long, narrow beard; rangy "
                "and restless.\n"
                "2. A broad, heavy-boned face; a strong brow and a nose that has been broken; thick curly hair; a full, "
                "square-cut beard; massive through the shoulders.\n"
                "3. Still strikingly handsome: a fine, aquiline face; wavy hair swept back off the forehead; a close, "
                "full beard; proud and wary.\n"
                "4. A weathered, deeply lined face; deep-set, hooded eyes; coarse, wiry hair; a thick, untrimmed beard; "
                "lean and hard, slightly stooped."),
            views=views_prompt(keep="the gold armband", face="guarded and intense", no="no crown"),
        ),
        refs=view_refs("saul", ["Three-Quarter Rear View in Purple Robe-1.png", "Saul in purple robes-2.png",
                                "Weathered guard in a purple robe-3.png",
                                "Weathered side-profile man in purple robe-4.png",
                                "Tall Bearded Man in Purple Robe-5.png"]),
    ),

    # ── Samuel (added for S2E9) ─────────────────────────────────────────────────────────────────────────────────────
    # Old, because Samuel is old in every story an episode is likely to tell after his boyhood ("I am old and gray",
    # 1 Samuel 12:2). Long white hair because no razor was to touch his head (1 Samuel 1:11). The robe is the point of
    # him on screen: Saul tears its hem at Gilgal (15:27), and at Endor "an old man is coming up, and he is wrapped in a
    # robe" (28:14) — so it is a colour and a border the eye can find in daylight and in firelight: charcoal goat hair,
    # a deep blue band at the hem.
    "samuel": dict(
        name="Samuel",
        who="man",
        poss="his",
        folder="Samuel_Character_Design",
        made="2026-10-13",
        # Written from the five saved views, like Saul's; saved beside them as Samuel_Character_Description.txt.
        description=(
            "Samuel is a very old man, about eighty, thin and upright, with deeply lined, weathered olive skin, dark brown "
            "eyes and bushy white eyebrows. Long, wavy white hair that has never been cut falls well past his shoulders "
            "and down his back, and a long, full white beard reaches his chest. His expression is steady and stern. He "
            "wears an ankle-length tunic of plain undyed cream linen with long, loose sleeves. Over it a coarse robe of "
            "dark charcoal-brown goat-hair wool is wrapped across his chest and over his shoulders and falls to his "
            "shins, with a narrow band of deep blue along its hem and a dark blue tassel at each corner. A plain rope "
            "belt is knotted at his waist, its long ends hanging loose. He wears worn brown leather sandals. No halo."),
        tag="old man with long white hair in the dark robe",
        design=dict(
            lineup=(
                "I'm designing the on-screen look of the prophet Samuel for a series of photorealistic short Bible films "
                "made with AI video tools. I need one character design I can reuse in every clip he is in, so first I "
                "want options to choose from.\n\n"
                + LINEUP_FRAME + "\n\n"
                "Each one is Samuel, the last judge of Israel and the prophet who anointed its first two kings, as he "
                "could have looked around 1020 BC: a very old man, about eighty, thin but upright, with weathered olive "
                "skin and dark eyes. He was promised to God before he was born and no razor ever touched his head, so "
                "all four have long white hair, never cut, falling well past the shoulders, and a long white beard. A "
                "severe, watchful face that has spent a lifetime telling kings what they did not want to hear. Each is "
                "an original face, not modelled on any actor or famous painting. No halo, no glow.\n\n"
                "All four wear the same costume, so the choice is about the man: an ankle-length tunic of plain undyed "
                "linen; over it a long robe of coarse, dark charcoal-brown goat-hair wool, wrapped around the body and "
                "over the left shoulder and falling to the ankles, with a narrow woven band of deep blue along its hem "
                "and a tassel at each of its corners; a plain rope belt; worn leather sandals.\n\n"
                "Make the four men clearly different:\n"
                "1. Gaunt and hawk-nosed; hair hanging loose and straight to the middle of the back; a long, thin beard; "
                "piercing eyes under heavy white brows.\n"
                "2. A broad, deeply lined face; thick hair gathered back into one long braid; a full beard; steady and "
                "unhurried.\n"
                "3. A narrow, ascetic face; fine, wispy hair to the shoulder blades; a long beard that parts at the chin "
                "into two points; a sharp, severe gaze.\n"
                "4. A round, weathered face with bushy white eyebrows; thick wavy hair; a full, broad beard; kind eyes "
                "that do not look away."),
            views=views_prompt(keep="the blue band at the hem of the robe", face="stern and steady", no="no halo"),
        ),
        refs=view_refs("samuel", ["White-haired elder in a woven robe, rear view-1.png",
                                  "White-bearded elder in cream linen robe-2.png",
                                  "White-bearded elder in woven robes-3.png",
                                  "White-haired elder in left profile-4.png",
                                  "White-Bearded Elder in Linen and Wool-5.png"]),
    ),
}


def standing_refs():
    """Every standing reference as a REFERENCES-shaped dict, keyed by id. A character whose images are not made yet
    (made=None, as Saul and Samuel were for S2E9's first page) comes through with made=False and his design prompts, so
    the cue sheet can put the prompts to make him at the top of Generate and the clip cards can already say which files
    to attach."""
    out = {}
    for key, ch in CHARACTERS.items():
        for r in ch["refs"]:
            out[r["id"]] = dict(
                id=r["id"], name=ch["name"], who=ch["who"], poss=ch.get("poss", "his"),
                title=f"{ch['name']} — {r['view'].split(';')[0].split(' — ')[0]}",
                file=ch["folder"] + "\\" + r["file"], prompt=r["view"], note=r.get("use", ""),
                made=bool(ch.get("made")), standing=True, character=key, folder=ch["folder"],
                description=ch.get("description"), design=ch.get("design"), tag=ch.get("tag"))
    return out
