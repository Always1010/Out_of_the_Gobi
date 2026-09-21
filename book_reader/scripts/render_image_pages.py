"""Render the approved visual-content pages for the offline reader."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / "book_reader"
PDF = ROOT / "走出戈壁-单伟健.pdf"
MANIFEST = BOOK / "images" / "images.json"
OUTPUT = BOOK / "images" / "pages"


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["pages"]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gobi-images-") as temporary:
        temp = Path(temporary)
        for entry in entries:
            page = entry["pdf_page"]
            rendered = temp / f"page-{page:03d}.png"
            subprocess.run(
                ["pdftoppm", "-f", str(page), "-l", str(page), "-r", "240", "-png", "-singlefile", str(PDF), str(rendered.with_suffix(""))],
                check=True,
            )
            target = OUTPUT / f"page-{page:03d}.jpg"
            with Image.open(rendered) as source:
                source.convert("RGB").save(target, quality=91, optimize=True)
            rendered.unlink(missing_ok=True)
            entry["status"] = "rendered"
            entry["asset"] = f"pages/{target.name}"
            print(f"Rendered PDF page {page}", flush=True)
    MANIFEST.write_text(json.dumps({"source_pdf": "../走出戈壁-单伟健.pdf", "pages": entries, "blank_pages": [18, 413]}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
