"""Build chaptered, page-flowing Markdown without PDF page markers.

The existing text/simplified and text/traditional trees are intentionally left
untouched.  This variant joins text across scanned page boundaries and places
image plates after any OCR text belonging to their source page.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from opencc import OpenCC

from assemble_transcript import PAGES, chapter_start, page_paragraphs

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / "book_reader"
CHAPTERS = BOOK / "text" / "chapters.json"
IMAGES = BOOK / "images" / "images.json"
OUTPUT = BOOK / "text" / "simplified-continuous"
BOOK_OUTPUT = BOOK / "text" / "book-simplified-continuous.md"


def repair_stars(text: str) -> str:
    """Normalize OCR variants of the book's three-star scene separator.

    The source book uses only ``★★★``.  OCR occasionally turns one or more
    stars into 大, X, or K, or loses a star altogether.  These marks occur on
    their own line, so regular prose is never changed.
    """
    if re.fullmatch(r"[★大XK]+", text.strip()) and "★" in text:
        return "★★★"
    return text


def clean(paragraph: str, converter: OpenCC) -> str:
    return repair_stars(converter.convert(paragraph))


def main() -> None:
    chapters = json.loads(CHAPTERS.read_text(encoding="utf-8"))
    image_pages = {item["pdf_page"] for item in json.loads(IMAGES.read_text(encoding="utf-8"))["pages"]}
    converter = OpenCC("t2s")
    resolved = []
    for chapter in chapters:
        start = chapter_start(chapter)
        if start is None:
            raise RuntimeError(f"Chapter title was not found: {chapter['title_traditional']}")
        resolved.append({**chapter, "pdf_page_start": start})
    resolved.sort(key=lambda item: item["pdf_page_start"])

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT.glob("*.md"):
        old.unlink()
    full_book: list[str] = []
    for index, chapter in enumerate(resolved):
        start = chapter["pdf_page_start"]
        end = resolved[index + 1]["pdf_page_start"] - 1 if index + 1 < len(resolved) else PAGES
        title = converter.convert(chapter["title_traditional"])
        content = [f"# {title}", ""]
        for page in range(start, end + 1):
            for paragraph in page_paragraphs(page):
                value = clean(paragraph, converter)
                # OCR sometimes repeats the chapter heading on its first page.
                if value in {title, title.split("：")[-1], re.sub(r"^第[一二三四五六七八九十百零]+章", "", title)}:
                    continue
                content.extend([value, ""])
            if page in image_pages:
                content.extend([f"<!-- Image plate: images/pages/page-{page:03d}.jpg -->", ""])
        filename = f"{index + 1:02d}-{chapter['id']}.md"
        output = "\n".join(content).rstrip() + "\n"
        (OUTPUT / filename).write_text(output, encoding="utf-8")
        full_book.extend(content + ["", "---", ""])
    BOOK_OUTPUT.write_text("\n".join(full_book).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {len(resolved)} continuous chapter files and {BOOK_OUTPUT.name}.")


if __name__ == "__main__":
    main()
