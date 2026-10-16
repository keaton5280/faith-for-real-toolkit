#!/usr/bin/env python3
"""Pack the toolkit into one text file (bundle.md) for the Claude Project, and unpack it again.

    python3 make_bundle.py pack   [bundle.md]      # from a working copy → one doc for project_write
    python3 make_bundle.py unpack bundle.md [dir]  # in a fresh session: recreate the working copy

The payload is a gzip+base64 tarball under a readable manifest (changed for S2E9). The plain-text bundle had grown past
the 256 KiB that project_read returns inline; it came back cut off, and the old unpacker silently dropped every file
after the cut. Packed this way the toolkit is about half of that, and a payload that does not decode fails loudly.
`unpack` still reads the old plain-text format. Fonts are binary and not bundled — setup_fonts.py fetches them.
"""
import base64, datetime, gzip, hashlib, io, os, re, sys, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["README.md", "style.py", "characters.py", "episode.py", "lint_prompts.py", "overlays.py", "framing.py",
         "maps.py", "charts.py", "render.py", "cuesheet.py", "check_anchors.py", "arrowgrid.py",
         "setup_fonts.py", "setup_geo.py", "make_bundle.py", "episodes/_template.py",
         "episodes/S2E3.py"]
OPEN, CLOSE = "<<<FILE: {}>>>", "<<<END FILE>>>"          # the old plain-text format, read by unpack()
P_OPEN, P_CLOSE = "<<<PAYLOAD>>>", "<<<END PAYLOAD>>>"

# The bootstrap spells its delimiters in two halves so it never matches its own text.
BOOTSTRAP = (
    "python3 - bundle.md <<'PY'\n"
    "import base64, io, re, sys, tarfile\n"
    "t = open(sys.argv[1]).read()\n"
    "m = re.search('<<' + '<PAYLOAD>>>\\n(.*?)\\n<<' + '<END PAYLOAD>>>', t, re.S)\n"
    "tf = tarfile.open(fileobj=io.BytesIO(base64.b64decode(''.join(m.group(1).split()))), mode='r:gz')\n"
    "try: tf.extractall('pipeline', filter='data')\n"
    "except TypeError: tf.extractall('pipeline')\n"
    "print('unpacked', len(tf.getnames()), 'files into pipeline/')\n"
    "PY\n")


def pack(out):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
        for f in FILES:
            data = open(os.path.join(HERE, f), "rb").read()
            info = tarfile.TarInfo(f); info.size = len(data); info.mtime = 0; info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    # mtime=0 in the gzip header too, so the same files always pack to the same bytes and the manifest hash says
    # whether the project's bundle is current.
    raw = gzip.compress(buf.getvalue(), compresslevel=9, mtime=0)
    b64 = base64.b64encode(raw).decode("ascii")
    lines = "\n".join(b64[i:i + 100] for i in range(0, len(b64), 100))
    manifest = "\n".join(f"- `{f}` — {os.path.getsize(os.path.join(HERE, f)):,} bytes" for f in FILES)
    doc = (f"# visual-pipeline bundle — packed {datetime.date.today().isoformat()}\n\n"
           "Every file of the Faith for Real visuals toolkit, as a gzip+base64 tarball under this manifest. Since 15 October "
           "2026 the toolkit's home is the private GitHub repo `keaton5280/faith-for-real-toolkit`; clone that when the "
           "session can attach it. This doc is the fallback snapshot, repacked after every push. To recreate the "
           "working copy from it, save this doc as bundle.md and run the bootstrap below, then "
           "`python3 pipeline/setup_fonts.py`. (It was plain text until 13 October 2026; at 300 KB it no longer came back "
           "whole from project_read.)\n\n"
           "```\n" + BOOTSTRAP + "```\n\n"
           f"## Manifest — {len(FILES)} files, sha256 of the tarball {hashlib.sha256(raw).hexdigest()[:16]}\n\n"
           + manifest + "\n\n" + P_OPEN + "\n" + lines + "\n" + P_CLOSE + "\n")
    open(out, "w").write(doc)
    print("packed", len(FILES), "files →", out, os.path.getsize(out), "bytes")


def unpack(src, dest):
    t = open(src).read()
    m = re.search(re.escape(P_OPEN) + r"\n(.*?)\n" + re.escape(P_CLOSE), t, re.S)
    if m:
        tf = tarfile.open(fileobj=io.BytesIO(base64.b64decode("".join(m.group(1).split()))), mode="r:gz")
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            tf.extractall(dest)
        print("unpacked", len(tf.getnames()), "files →", dest)
        return
    n = 0
    for name, body in re.findall(r"<<<FILE: (.+?)>>>\n(.*?)\n<<<END FILE>>>", t, re.S):
        p = os.path.join(dest, name); os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        open(p, "w").write(body + "\n"); n += 1
    print("unpacked", n, "files →", dest)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("pack", "unpack"): sys.exit(__doc__)
    if sys.argv[1] == "pack": pack(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "bundle.md"))
    else: unpack(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "pipeline")
