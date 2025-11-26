#!/usr/bin/env python3
"""
Convert an input image (ICO/PNG) into a multi-size Windows ICO containing standard sizes.
Requires: Pillow

Usage:
  venv\Scripts\python.exe tools\convert_ico.py input.ico output.ico
  venv\Scripts\python.exe tools\convert_ico.py input.png output.ico
"""
import sys
from pathlib import Path

SIZES = [16, 24, 32, 48, 64, 128, 256]

def main():
    try:
        from PIL import Image
    except Exception as e:
        print("[ERROR] Pillow not installed. Install with: venv\\Scripts\\pip.exe install pillow", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) != 3:
        print("Usage: convert_ico.py <input.(ico|png)> <output.ico>")
        sys.exit(2)

    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])

    if not inp.exists():
        print(f"[ERROR] Input not found: {inp}", file=sys.stderr)
        sys.exit(3)

    # Load first frame as base
    im = Image.open(inp)
    if im.mode not in ("RGBA", "RGB"):
        im = im.convert("RGBA")

    # Generate resized images
    images = []
    for sz in SIZES:
        images.append(im.resize((sz, sz), Image.LANCZOS))

    # Save as multi-size ICO
    images[0].save(outp, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"[OK] Wrote: {outp}")

if __name__ == "__main__":
    main()
