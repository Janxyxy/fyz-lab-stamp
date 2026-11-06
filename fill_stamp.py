#!/usr/bin/env python3
"""Fill the CTU physics-lab stamp (razitko) image with text from a JSON file.

Usage:
    python fill_stamp.py                                  # razitko.jpg + data.json -> razitko_filled.png
    python fill_stamp.py razitko.jpg data.json -o out.png
    python fill_stamp.py --set task_number=3 --set "task_name=Kyvadlo"

Requires: pip install -r requirements.txt

JSON keys (all optional, missing/empty keys are left blank):
    name, measurement_date, study_year, year, submission_date,
    study_group, lab_group, classification, task_number, task_name

Extra key: semester (1, 2, 3, ...) - with task_number, looks up task_name in tasks.json.

Automatic values (only when the key is empty/missing):
    task_name        -> from tasks.json using semester + task_number
    submission_date  -> today's date
    study_year       -> academic year of measurement_date (or today), e.g. 2026/2027
"""
import argparse
import json
import re
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Reference size of the original stamp image. All boxes below are in these pixels,
# so the script keeps working if you pass a bigger/smaller version of the same image.
REF_W, REF_H = 513, 249

# key: (x0, y0, x1, y1, max_font_px, baseline_offset)
# Box = the table cell; the value's baseline is placed baseline_offset px below y0,
# so every font sits on the same line regardless of its ascent/descent metrics.
FIELDS = {
    "name":             (6,   90, 350, 118, 11, 24),
    "measurement_date": (350, 90, 506, 118, 11, 24),
    "study_year":       (6,  118, 172, 146, 11, 24),
    "year":             (172, 118, 350, 146, 11, 24),
    "submission_date":  (350, 118, 506, 146, 11, 24),
    "study_group":      (6,  146, 172, 174, 11, 24),
    "lab_group":        (172, 146, 350, 174, 11, 24),
    "classification":   (350, 146, 506, 174, 11, 24),
    "task_number":      (6,  201, 89,  241, 14, 33),
    "task_name":        (89, 201, 506, 241, 13, 33),
}

# Fields that may wrap onto two lines when a single line would get too small.
WRAPPABLE = {"task_name"}
MIN_SINGLE_LINE_PX = 10   # below this, wrap (if allowed) instead of shrinking further
MIN_PX = 6
PAD = 4

# Keys that are allowed in the JSON but not drawn (used to derive other values).
EXTRA_KEYS = {"semester"}

FONT_CANDIDATES = [
    "segoeui.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "LiberationSans-Regular.ttf",
]

DATE_FMT = "{d:02d}. {m:02d}. {y}"


@lru_cache(maxsize=None)
def load_font(size: int, font_path: str | None) -> ImageFont.FreeTypeFont:
    candidates = [font_path] if font_path else FONT_CANDIDATES
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    sys.exit("No usable TrueType font found. Pass one with --font path/to/font.ttf "
             "(it must support Czech characters).")


def parse_date(s: str) -> date | None:
    """Parse '6. 11. 2026', '06.11.2026' or '2026-11-06'."""
    s = s.strip()
    m = re.fullmatch(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s)
    if m:
        d, mo, y = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
        if not m:
            return None
        y, mo, d = map(int, m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


TASKS_FILE = Path(__file__).with_name("tasks.json")


def load_tasks() -> dict:
    """{semester: {task_number: task_name}} from tasks.json, or {} if missing."""
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def lookup_task_name(semester, task_number) -> str:
    return load_tasks().get(str(semester).strip(), {}).get(str(task_number).strip(), "")


def fill_defaults(data: dict, warn: bool = True) -> dict:
    data = dict(data)
    today = date.today()
    if not str(data.get("task_name", "")).strip() and str(data.get("semester", "")).strip():
        name = lookup_task_name(data["semester"], data.get("task_number", ""))
        if name:
            data["task_name"] = name
        elif warn:
            print(f"Warning: no task {data.get('task_number')!r} in semester {data['semester']!r} "
                  f"(see {TASKS_FILE.name}).", file=sys.stderr)
    if not str(data.get("submission_date", "")).strip():
        data["submission_date"] = DATE_FMT.format(d=today.day, m=today.month, y=today.year)
    if not str(data.get("study_year", "")).strip():
        ref = parse_date(str(data.get("measurement_date", ""))) or today
        start = ref.year if ref.month >= 9 else ref.year - 1   # academic year starts in September
        data["study_year"] = f"{start}/{start + 1}"
    return data


def split_two_lines(text: str, draw, font) -> tuple[str, str]:
    """Split text at the word boundary that makes the longer line as short as possible."""
    words = text.split()
    best = (text, "")
    best_w = float("inf")
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        w = max(draw.textlength(a, font=font), draw.textlength(b, font=font))
        if w < best_w:
            best, best_w = (a, b), w
    return best


def draw_field(draw, key, text, k, font_path, color):
    x0, y0, x1, y1, max_px, base = FIELDS[key]
    max_w = (x1 - x0 - 2 * PAD) * k
    x = (x0 + PAD) * k

    def font_at(px):
        return load_font(max(1, round(px * k)), font_path)

    # 1) single line, shrinking down to the readable minimum
    min_single = MIN_SINGLE_LINE_PX if key in WRAPPABLE and " " in text else MIN_PX
    size = max_px
    while size >= min_single:
        font = font_at(size)
        if draw.textlength(text, font=font) <= max_w:
            draw.text((x, (y0 + base) * k), text, font=font, fill=color, anchor="ls")
            return
        size -= 0.5

    if min_single == MIN_PX:   # not wrappable: draw at minimum size and warn
        draw.text((x, (y0 + base) * k), text, font=font_at(MIN_PX), fill=color, anchor="ls")
        print(f"Warning: '{key}' does not fit its box even at {MIN_PX}px.", file=sys.stderr)
        return

    # 2) two lines, bottom line sits just above the cell's bottom border
    size = min(max_px, 11)
    while True:
        font = font_at(size)
        a, b = split_two_lines(text, draw, font)
        fits = max(draw.textlength(a, font=font), draw.textlength(b, font=font)) <= max_w
        if fits or size <= MIN_PX:
            break
        size -= 0.5
    if not fits:
        print(f"Warning: '{key}' does not fit its box even on two lines.", file=sys.stderr)
    base2 = y1 - y0 - 3.5
    base1 = base2 - size * 1.15
    draw.text((x, (y0 + base1) * k), a, font=font, fill=color, anchor="ls")
    draw.text((x, (y0 + base2) * k), b, font=font, fill=color, anchor="ls")


def fill_stamp(image_path, data, out_path, font_path=None, color=(10, 10, 120), scale=4):
    img = render_stamp(image_path, data, font_path, color, scale)
    try:
        img.save(out_path)
    except OSError as e:
        sys.exit(f"Cannot write {out_path}: {e}\n"
                 "Is the file open in another program (image viewer, editor preview)? "
                 "Close it or use -o to write a different file.")
    return out_path


def render_stamp(image_path, data, font_path=None, color=(10, 10, 120), scale=4) -> Image.Image:
    """Return the filled stamp as a PIL image (no defaults applied, no file written)."""
    img = Image.open(image_path).convert("RGB")
    # Work on an upscaled copy so the text stays sharp when printed.
    k = scale * img.width / REF_W          # reference px -> output px
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    for key in FIELDS:
        text = str(data.get(key, "")).strip()
        if text:
            draw_field(draw, key, text, k, font_path, color)
    return img


def parse_set(items: list[str]) -> dict:
    out = {}
    for item in items:
        if "=" not in item:
            sys.exit(f"--set expects key=value, got: {item!r}")
        key, value = item.split("=", 1)
        out[key.strip()] = value
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("image", nargs="?", default="razitko.jpg",
                   help="blank stamp image (default: razitko.jpg)")
    p.add_argument("json", nargs="?", default="data.json",
                   help="JSON file with the values (default: data.json)")
    p.add_argument("-o", "--output", default=None, help="output PNG (default: <image>_filled.png)")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                   help="override a value from the JSON (repeatable)")
    p.add_argument("--font", default=None, help="TTF font with Czech support (optional)")
    p.add_argument("--color", default="0a0a78", help="text color as hex RGB (default 0a0a78)")
    p.add_argument("--scale", type=float, default=4,
                   help="output resolution multiplier (default 4)")
    args = p.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        hint = " Copy data.example.json to data.json and fill it in." if args.json == "data.json" else ""
        sys.exit(f"{json_path} not found.{hint}")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data.update(parse_set(args.set))

    unknown = set(data) - set(FIELDS) - EXTRA_KEYS
    if unknown:
        print(f"Warning: unknown keys ignored: {', '.join(sorted(unknown))}", file=sys.stderr)
    data = fill_defaults(data)

    out = args.output or str(Path(args.image).with_name(Path(args.image).stem + "_filled.png"))
    hexc = args.color.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", hexc):
        sys.exit(f"--color expects 6 hex digits, got: {args.color!r}")
    color = tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    fill_stamp(args.image, data, out, args.font, color, args.scale)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
