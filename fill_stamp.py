#!/usr/bin/env python3
"""Fill the CTU physics-lab stamp (razitko) image with text from a JSON file.

Usage:
    python fill_stamp.py razitko.jpg data.json            # -> razitko_filled.png
    python fill_stamp.py razitko.jpg data.json -o out.png

Requires: pip install pillow

JSON keys (all optional, missing/empty keys are left blank):
    name, measurement_date, study_year, year, submission_date,
    study_group, lab_group, classification, task_number, task_name
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Reference size of the original stamp image. All boxes below are in these pixels,
# so the script keeps working if you pass a bigger/smaller version of the same image.
REF_W, REF_H = 513, 249

# key: (x0, y0, x1, y1, max_font_px, value_top_offset)
# Box = the table cell; the value is drawn under the printed label.
FIELDS = {
    "name":             (6,   90, 350, 118, 11, 13),
    "measurement_date": (350, 90, 506, 118, 11, 13),
    "study_year":       (6,  118, 172, 146, 11, 13),
    "year":             (172, 118, 350, 146, 11, 13),
    "submission_date":  (350, 118, 506, 146, 11, 13),
    "study_group":      (6,  146, 172, 174, 11, 13),
    "lab_group":        (172, 146, 350, 174, 11, 13),
    "classification":   (350, 146, 506, 174, 11, 13),
    "task_number":      (6,  201, 89,  241, 14, 17),
    "task_name":        (89, 201, 506, 241, 13, 17),
}

FONT_CANDIDATES = [
    "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "LiberationSans-Regular.ttf",
]


def load_font(size: int, font_path: str | None) -> ImageFont.FreeTypeFont:
    candidates = [font_path] if font_path else FONT_CANDIDATES
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    sys.exit("No usable TrueType font found. Pass one with --font path/to/font.ttf "
             "(it must support Czech characters).")


def fill_stamp(image_path, data, out_path, font_path=None, color=(10, 10, 120), scale=4):
    img = Image.open(image_path).convert("RGB")
    # Work on an upscaled copy so the text stays sharp when printed.
    k = scale * img.width / REF_W          # reference px -> output px
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    for key, (x0, y0, x1, y1, max_px, top) in FIELDS.items():
        text = str(data.get(key, "")).strip()
        if not text:
            continue
        pad = 4
        max_w = (x1 - x0 - 2 * pad) * k
        size = max_px
        while True:
            font = load_font(max(1, round(size * k)), font_path)
            if draw.textlength(text, font=font) <= max_w or size <= 6:
                break
            size -= 0.5
        draw.text(((x0 + pad) * k, (y0 + top) * k), text, font=font, fill=color)

    img.save(out_path)
    return out_path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("image", help="blank stamp image (jpg/png)")
    p.add_argument("json", help="JSON file with the values")
    p.add_argument("-o", "--output", default=None, help="output PNG (default: <image>_filled.png)")
    p.add_argument("--font", default=None, help="TTF font with Czech support (optional)")
    p.add_argument("--color", default="0a0a78", help="text color as hex RGB (default 0a0a78)")
    args = p.parse_args()

    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    unknown = set(data) - set(FIELDS)
    if unknown:
        print(f"Warning: unknown keys ignored: {', '.join(sorted(unknown))}", file=sys.stderr)

    out = args.output or str(Path(args.image).with_name(Path(args.image).stem + "_filled.png"))
    hexc = args.color.lstrip("#")
    color = tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    fill_stamp(args.image, data, out, args.font, color)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
