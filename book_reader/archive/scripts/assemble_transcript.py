"""Historical OCR-to-manuscript rebuild; overwrites generated manuscript files."""
from __future__ import annotations

import json
import shutil
from opencc import OpenCC

# Archived tools remain runnable from any working directory.
import sys
from pathlib import Path

BOOK = Path(__file__).resolve().parents[2]
ROOT = BOOK.parent
sys.path.insert(0, str(BOOK / "scripts"))
from ocr_common import (
    RAW, CHAPTERS, IMAGES, TRADITIONAL, SIMPLIFIED, PAGES,
    chapter_start, reading_paragraphs, to_mainland_simplified,
)


def main() -> None:
    missing = [page for page in range(1, PAGES + 1) if not (RAW / f"page-{page:03d}.json").exists()]
    if missing:
        raise RuntimeError(f"OCR is incomplete; {len(missing)} pages are missing, first: {missing[:10]}")
    chapters = json.loads(CHAPTERS.read_text(encoding="utf-8"))
    image_records = {item["pdf_page"]: item for item in json.loads(IMAGES.read_text(encoding="utf-8"))["pages"]}
    for directory in (TRADITIONAL, SIMPLIFIED):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    resolved = []
    for chapter in chapters:
        start = chapter_start(chapter)
        if start is None:
            raise RuntimeError(f"Chapter title was not found: {chapter['title_traditional']}")
        resolved.append({**chapter, "pdf_page_start": start, "status": "located"})
    resolved.sort(key=lambda item: item["pdf_page_start"])
    CHAPTERS.write_text(json.dumps(resolved, ensure_ascii=False, indent=2), encoding="utf-8")

    # tw2sp additionally converts Taiwan glyph variants such as 簷 → 檐.
    converter = OpenCC("tw2sp")
    book_traditional = []
    book_simplified = []
    for index, chapter in enumerate(resolved):
        start = chapter["pdf_page_start"]
        end = resolved[index + 1]["pdf_page_start"] - 1 if index + 1 < len(resolved) else PAGES
        title_traditional = chapter["title_traditional"]
        title_simplified = to_mainland_simplified(title_traditional, converter)
        traditional = [f"# {title_traditional}", ""]
        simplified = [f"# {title_simplified}", ""]
        for page in range(start, end + 1):
            traditional.append(f"<!-- PDF {page} -->")
            simplified.append(f"<!-- PDF {page} -->")
            image = image_records.get(page)
            for paragraph in reading_paragraphs(page, image["kind"] if image else None):
                traditional.extend([paragraph, ""])
                simplified.extend([to_mainland_simplified(paragraph, converter), ""])
            if image:
                marker = f"<!-- Image plate: images/pages/page-{page:03d}.jpg -->"
                traditional.extend([marker, ""])
                simplified.extend([marker, ""])
        base = f"{index + 1:02d}-{chapter['id']}"
        (TRADITIONAL / f"{base}.md").write_text("\n".join(traditional).rstrip() + "\n", encoding="utf-8")
        (SIMPLIFIED / f"{base}.md").write_text("\n".join(simplified).rstrip() + "\n", encoding="utf-8")
        book_traditional.extend(traditional + ["", "---", ""])
        book_simplified.extend(simplified + ["", "---", ""])
    (BOOK / "text" / "book-traditional.md").write_text("\n".join(book_traditional).rstrip() + "\n", encoding="utf-8")
    (BOOK / "text" / "book-simplified.md").write_text("\n".join(book_simplified).rstrip() + "\n", encoding="utf-8")
    # Reapply reviewed, page-scoped fixes after the reproducible OCR baseline.
    # The OCR JSON itself remains unchanged as source evidence.
    from proofreading import apply_patches
    corrected = apply_patches()
    print(f"Wrote {len(resolved)} chapter files in both scripts; applied {corrected} reviewed corrections.")


if __name__ == "__main__":
    main()
