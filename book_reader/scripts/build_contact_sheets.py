"""Create low-resolution contact sheets for visual image-page triage."""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "走出戈壁-单伟健.pdf"
OUTPUT = ROOT / "book_reader" / "images" / "contact_sheets"
PAGES = 420
PER_SHEET = 12
COLS = 3
THUMB_W = 220
THUMB_H = 311


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    with tempfile.TemporaryDirectory(prefix="gobi-thumbs-") as temporary:
        temp = Path(temporary)
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", str(PAGES), "-r", "72", "-jpeg", str(PDF), str(temp / "page")],
            check=True,
        )
        rendered = sorted(temp.glob("page-*.jpg"))
        if len(rendered) != PAGES:
            raise RuntimeError(f"Expected {PAGES} rendered pages, got {len(rendered)}")
        for sheet_number, offset in enumerate(range(0, PAGES, PER_SHEET), start=1):
            group = rendered[offset : offset + PER_SHEET]
            rows = math.ceil(len(group) / COLS)
            canvas = Image.new("RGB", (COLS * THUMB_W, rows * (THUMB_H + 22)), "white")
            draw = ImageDraw.Draw(canvas)
            for position, path in enumerate(group):
                page = offset + position + 1
                column = position % COLS
                row = position // COLS
                x = column * THUMB_W
                y = row * (THUMB_H + 22)
                with Image.open(path) as source:
                    image = source.convert("RGB")
                    image.thumbnail((THUMB_W - 8, THUMB_H - 8))
                    canvas.paste(image, (x + (THUMB_W - image.width) // 2, y + 4))
                draw.text((x + 6, y + THUMB_H + 3), f"PDF {page}", fill="black", font=font)
            canvas.save(OUTPUT / f"sheet-{sheet_number:02d}-pages-{offset + 1:03d}-{offset + len(group):03d}.jpg", quality=88)
            print(f"Wrote sheet {sheet_number}", flush=True)
    print(f"Wrote {math.ceil(PAGES / PER_SHEET)} contact sheets to {OUTPUT}")


if __name__ == "__main__":
    main()
