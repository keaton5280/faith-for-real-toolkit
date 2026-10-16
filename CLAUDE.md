# Faith for Real visuals toolkit

This repo is the source of truth for the toolkit behind the Faith for Real episode cue sheets and asset packs. How
it is used — the shot plan, the cue sheet, the read-back — is the `episode-visuals` skill, and the reasons behind each
rule are `claude/episode-visuals-process.md` in the YouTube Analytics project. `README.md` documents every file.

- **Setup**: `python3 setup_fonts.py` (fonts are fetched, never committed); `python3 setup_geo.py` before any map cue.
- **House style lives in `style.py`.** Change a rule there, never per episode.
- **Before committing a change**, run `python3 episode.py` on `episodes/S2E3.py` and `episodes/_template.py`. If
  `overlays.py` or `framing.py` changed, render S2E3 before and after and diff: old episodes must stay pixel-identical
  unless the change is meant to alter them, and the commit message says so when it is.
- **After every push**, refresh the project's fallback copy so the two never drift: `python3 make_bundle.py pack
  /tmp/bundle.md`, then `project_write` it to `claude/visual-pipeline/bundle.md`, and `project_write` `README.md` to
  `claude/visual-pipeline/README.md` if it changed.
- Episode files other than the S2E3 example and the template live in the project as `claude/episodes/S#E#.py`, not here.
- Commit messages say what changed for Keaton in plain words.
