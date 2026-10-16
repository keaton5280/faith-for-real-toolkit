#!/usr/bin/env python3
"""Fetch EB Garamond and Inter into fonts/ (Google Fonts is blocked from the sandbox;
the @fontsource npm packages are not). Idempotent — skips if the files exist.

    python3 setup_fonts.py
"""
import glob, importlib, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
WANT = ["eb-garamond-latin-400-normal", "eb-garamond-latin-400-italic", "eb-garamond-latin-500-normal",
        "eb-garamond-latin-500-italic", "eb-garamond-latin-600-normal", "eb-garamond-latin-700-normal",
        "inter-latin-400-normal", "inter-latin-500-normal", "inter-latin-600-normal", "inter-latin-700-normal"]


def main():
    os.makedirs(FONTS, exist_ok=True)
    missing = [w for w in WANT if not os.path.exists(os.path.join(FONTS, w + ".ttf"))]
    if not missing:
        print("fonts present"); return
    # woff2 needs BOTH fontTools and brotli; a sandbox can have the first without the second (it did on 15 Oct).
    # -I keeps this folder off sys.path, so `-m pip` is the real pip even when run from here.
    try:
        import brotli  # noqa
        from fontTools.ttLib import woff2  # noqa
    except ImportError:
        subprocess.run([sys.executable, "-I", "-m", "pip", "install", "--quiet", "--break-system-packages",
                        "fonttools", "brotli"], check=True)
        importlib.invalidate_caches()
        import brotli  # noqa
        from fontTools.ttLib import woff2  # noqa
    tmp = tempfile.mkdtemp()
    subprocess.run(["npm", "init", "-y"], cwd=tmp, check=True, capture_output=True)
    subprocess.run(["npm", "install", "--no-audit", "--no-fund", "@fontsource/eb-garamond", "@fontsource/inter"],
                   cwd=tmp, check=True, capture_output=True)
    from fontTools.ttLib import woff2
    for w in missing:
        fam = "eb-garamond" if w.startswith("eb") else "inter"
        src = glob.glob(os.path.join(tmp, "node_modules", "@fontsource", fam, "files", w + ".woff2"))
        if not src:
            print("not found in package:", w); continue
        woff2.decompress(src[0], os.path.join(FONTS, w + ".ttf"))
        print("fetched", w)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
