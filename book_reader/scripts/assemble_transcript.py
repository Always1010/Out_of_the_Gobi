"""Assemble page OCR into chapter Markdown and derive Simplified Chinese text."""

from __future__ import annotations

import json
import re
import shutil
import statistics
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / "book_reader"
RAW = BOOK / "ocr" / "paddle_small"
CHAPTERS = BOOK / "text" / "chapters.json"
IMAGES = BOOK / "images" / "images.json"
TRADITIONAL = BOOK / "text" / "traditional"
SIMPLIFIED = BOOK / "text" / "simplified"
PAGES = 420


def load_page(page: int) -> tuple[list[str], list[float], list[list[list[float]]]]:
    payload = json.loads((RAW / f"page-{page:03d}.json").read_text(encoding="utf-8"))
    result = payload["res"]
    return result.get("rec_texts", []), result.get("rec_scores", []), result.get("dt_polys", [])


def normalized(value: str) -> str:
    return re.sub(r"[\s：:，,。\.]+", "", value)


def chapter_start(chapter: dict) -> int | None:
    if chapter.get("fixed_pdf_page_start"):
        return int(chapter["fixed_pdf_page_start"])
    # OCR often puts a section label and its title on separate lines.  Search the
    # distinctive title portion after the full-width colon when present.
    title = normalized(chapter["title_traditional"].split("：")[-1])
    expected = chapter.get("pdf_page_start") or chapter["printed_page_start"]
    candidates: list[tuple[int, float]] = []
    for page in range(max(1, expected - 24), min(PAGES, expected + 24) + 1):
        lines, _scores, polygons = load_page(page)
        for index, line in enumerate(lines):
            if title and title in normalized(line):
                y = polygons[index][0][1] if index < len(polygons) else 9999
                candidates.append((page, y))
    if not candidates:
        return None
    # A chapter heading is normally near the top or center, while a mention in body text is lower.
    candidates.sort(key=lambda item: (abs(item[0] - expected), item[1]))
    return candidates[0][0]


def page_paragraphs(page: int) -> list[str]:
    lines, scores, polygons = load_page(page)
    positioned = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        polygon = polygons[index] if index < len(polygons) else []
        x = polygon[0][0] if polygon else 0
        y = polygon[0][1] if polygon else 999
        score = scores[index] if index < len(scores) else 1.0
        # Page headers, page numbers, and OCR noise at the foot are not reading text.
        if y < 330 or y > 2870 or score < 0.35:
            continue
        positioned.append((y, x, line.strip()))
    positioned.sort()
    if not positioned:
        return []
    gaps = [positioned[index + 1][0] - positioned[index][0] for index in range(len(positioned) - 1)]
    normal_gap = statistics.median(gaps) if gaps else 58
    paragraphs: list[list[str]] = [[]]
    previous_y = positioned[0][0]
    for y, _x, line in positioned:
        if paragraphs[-1] and y - previous_y > max(90, normal_gap * 1.65):
            paragraphs.append([])
        paragraphs[-1].append(line)
        previous_y = y
    return ["".join(paragraph) for paragraph in paragraphs if paragraph]


def main() -> None:
    missing = [page for page in range(1, PAGES + 1) if not (RAW / f"page-{page:03d}.json").exists()]
    if missing:
        raise RuntimeError(f"OCR is incomplete; {len(missing)} pages are missing, first: {missing[:10]}")
    chapters = json.loads(CHAPTERS.read_text(encoding="utf-8"))
    image_pages = {item["pdf_page"] for item in json.loads(IMAGES.read_text(encoding="utf-8"))["pages"]}
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

    converter = OpenCC("t2s")
    book_traditional = []
    book_simplified = []
    for index, chapter in enumerate(resolved):
        start = chapter["pdf_page_start"]
        end = resolved[index + 1]["pdf_page_start"] - 1 if index + 1 < len(resolved) else PAGES
        title_traditional = chapter["title_traditional"]
        title_simplified = converter.convert(title_traditional)
        traditional = [f"# {title_traditional}", ""]
        simplified = [f"# {title_simplified}", ""]
        for page in range(start, end + 1):
            traditional.append(f"<!-- PDF {page} -->")
            simplified.append(f"<!-- PDF {page} -->")
            if page in image_pages:
                marker = f"<!-- Image plate: images/pages/page-{page:03d}.jpg -->"
                traditional.extend([marker, ""])
                simplified.extend([marker, ""])
                continue
            for paragraph in page_paragraphs(page):
                traditional.extend([paragraph, ""])
                simplified.extend([converter.convert(paragraph), ""])
        base = f"{index + 1:02d}-{chapter['id']}"
        (TRADITIONAL / f"{base}.md").write_text("\n".join(traditional).rstrip() + "\n", encoding="utf-8")
        (SIMPLIFIED / f"{base}.md").write_text("\n".join(simplified).rstrip() + "\n", encoding="utf-8")
        book_traditional.extend(traditional + ["", "---", ""])
        book_simplified.extend(simplified + ["", "---", ""])
    (BOOK / "text" / "book-traditional.md").write_text("\n".join(book_traditional).rstrip() + "\n", encoding="utf-8")
    (BOOK / "text" / "book-simplified.md").write_text("\n".join(book_simplified).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {len(resolved)} chapter files in both scripts.")


if __name__ == "__main__":
    main()
