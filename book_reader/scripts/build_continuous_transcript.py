"""Build Simplified and Traditional chapter manuscripts without page breaks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from opencc import OpenCC

from assemble_transcript import PAGES, chapter_start, normalized, reading_paragraphs, repair_star_break, to_mainland_simplified

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / "book_reader"
CHAPTERS = BOOK / "text" / "chapters.json"
IMAGES = BOOK / "images" / "images.json"
VARIANTS = (
    ("traditional-continuous", "book-traditional-continuous.md", None),
    ("simplified-continuous", "book-simplified-continuous.md", OpenCC("tw2sp")),
)
SENTENCE_ENDINGS = ("。", "！", "？", "；", "：", "…", ".", "!", "?", ";", ":", "”", "』", "」", "）", ")")


def clean(paragraph: str, converter: OpenCC | None) -> str:
    value = repair_star_break(paragraph)
    return to_mainland_simplified(value, converter) if converter else value


def ends_sentence(value: str) -> bool:
    """Only retain a paragraph break when the prior page actually ended it."""
    return value.rstrip().endswith(SENTENCE_ENDINGS)


def is_chapter_heading(value: str, title: str) -> bool:
    return normalized(value) in {normalized(title), normalized(title.split("：")[-1])} or bool(re.fullmatch(r"第[一二三四五六七八九十百零]+章", value))


def render_chapter(chapter: dict, start: int, end: int, image_records: dict[int, dict], converter: OpenCC | None) -> str:
    title = clean(chapter["title_traditional"], converter)
    blocks = [f"# {title}"]
    previous_text_index: int | None = None
    previous_page_had_image = False
    for page in range(start, end + 1):
        image = image_records.get(page)
        page_values = [clean(paragraph, converter) for paragraph in reading_paragraphs(page, image["kind"] if image else None)]
        page_values = [value for value in page_values if value]
        for paragraph_index, value in enumerate(page_values):
            if is_chapter_heading(value, title):
                continue
            if value == "★★★":
                blocks.append(value)
                previous_text_index = None
                continue
            # First paragraph on the next physical page belongs to the prior
            # paragraph if the prior page did not end a sentence.  This is the
            # page-break gap that made the earlier continuous version read
            # discontinuously.
            can_join = (
                paragraph_index == 0
                and previous_text_index is not None
                and not previous_page_had_image
                and not ends_sentence(blocks[previous_text_index])
            )
            if can_join:
                blocks[previous_text_index] += value
            else:
                blocks.append(value)
                previous_text_index = len(blocks) - 1
        previous_page_had_image = image is not None
        if previous_page_had_image:
            blocks.append(f"<!-- Image plate: images/pages/page-{page:03d}.jpg -->")
            previous_text_index = None
    return "\n\n".join(blocks).rstrip() + "\n"


def main() -> None:
    chapters = json.loads(CHAPTERS.read_text(encoding="utf-8"))
    image_records = {item["pdf_page"]: item for item in json.loads(IMAGES.read_text(encoding="utf-8"))["pages"]}
    resolved: list[dict] = []
    for chapter in chapters:
        start = chapter_start(chapter)
        if start is None:
            raise RuntimeError(f"Chapter title was not found: {chapter['title_traditional']}")
        resolved.append({**chapter, "pdf_page_start": start})
    resolved.sort(key=lambda item: item["pdf_page_start"])

    for directory_name, book_name, converter in VARIANTS:
        output_dir = BOOK / "text" / directory_name
        output_dir.mkdir(parents=True, exist_ok=True)
        for old in output_dir.glob("*.md"):
            old.unlink()
        full_book = []
        for index, chapter in enumerate(resolved):
            start = chapter["pdf_page_start"]
            end = resolved[index + 1]["pdf_page_start"] - 1 if index + 1 < len(resolved) else PAGES
            rendered = render_chapter(chapter, start, end, image_records, converter)
            filename = f"{index + 1:02d}-{chapter['id']}.md"
            (output_dir / filename).write_text(rendered, encoding="utf-8")
            full_book.extend([rendered.rstrip(), "", "---", ""])
        (BOOK / "text" / book_name).write_text("\n".join(full_book).rstrip() + "\n", encoding="utf-8")
        print(f"Wrote {len(resolved)} files in {directory_name} and {book_name}.")


if __name__ == "__main__":
    main()
