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
# Text on these full-page photo or photo-plate scans is a caption, page number,
# or decorative matter.  It belongs to the preserved image asset, not prose.
INLINE_IMAGE_TEXT_REMOVALS = {
    9: ("作者與耶倫，師徒聚首。",),
}


def load_page(page: int) -> tuple[list[str], list[float], list[list[list[float]]]]:
    payload = json.loads((RAW / f"page-{page:03d}.json").read_text(encoding="utf-8"))
    result = payload["res"]
    return result.get("rec_texts", []), result.get("rec_scores", []), result.get("dt_polys", [])


def normalized(value: str) -> str:
    return re.sub(r"[\s：:，,。\.]+", "", value)


def chinese_number(number: int) -> str:
    digits = "一二三四五六七八九"
    if number < 10:
        return digits[number - 1]
    if number < 20:
        return "十" + (digits[number - 11] if number > 10 else "")
    tens, ones = divmod(number, 10)
    return digits[tens - 1] + "十" + (digits[ones - 1] if ones else "")


def repair_star_break(value: str) -> str:
    """Normalize OCR variants of the book's three-star scene separator."""
    # On PDF 41 and 81 PaddleOCR read two separator glyphs as digit 1.
    if re.fullmatch(r"[★大XK]+", value.strip()) or value.strip() in {"1大X", "大11"}:
        return "★★★"
    return value


def normalize_round_brackets(value: str) -> str:
    """Use matching fullwidth round brackets in the Chinese reading text."""
    return value.translate(str.maketrans({"(": "（", ")": "）"}))


def to_mainland_simplified(value: str, converter: OpenCC) -> str:
    """Apply the small set of Mainland usage choices OpenCC leaves unchanged."""
    return converter.convert(value).translate(str.maketrans({
        "牠": "它", "衞": "卫", "敍": "叙", "擡": "抬",
    }))


def chapter_start(chapter: dict) -> int | None:
    if chapter.get("fixed_pdf_page_start"):
        return int(chapter["fixed_pdf_page_start"])
    # Running headers repeat chapter titles on later pages.  Their OCR boxes
    # sit above the body (usually y < 330), so they must never define a start.
    title = normalized(chapter["title_traditional"].split("：")[-1])
    expected = chapter.get("pdf_page_start") or chapter["printed_page_start"]
    label = f"第{chinese_number(chapter['number'])}章" if "number" in chapter else None
    numbered: list[tuple[int, float]] = []
    titles: list[tuple[int, float]] = []
    for page in range(max(1, expected - 24), min(PAGES, expected + 24) + 1):
        lines, _scores, polygons = load_page(page)
        body: list[tuple[str, float]] = []
        for index, line in enumerate(lines):
            y = polygons[index][0][1] if index < len(polygons) else 9999
            if 330 <= y <= 1400:
                body.append((normalized(line), y))
        page_titles = [(text, y) for text, y in body if title and title in text]
        titles.extend((page, y) for _text, y in page_titles)
        if label:
            # OCR may drop title characters on an opening page, but the
            # centered chapter number is consistently visible around y=375.
            numbered.extend((page, y) for text, y in body if 330 <= y <= 850 and text.startswith(label))
    candidates = numbered if label else titles
    if not candidates:
        return None
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
    return [repair_star_break("".join(paragraph)) for paragraph in paragraphs if paragraph]


def reading_paragraphs(page: int, image_kind: str | None = None) -> list[str]:
    """Return prose only, keeping images and their captions as image assets."""
    if image_kind and image_kind != "inline_portrait":
        return []
    values = page_paragraphs(page)
    for phrase in INLINE_IMAGE_TEXT_REMOVALS.get(page, ()):
        values = [value.replace(phrase, "") for value in values]
    return [normalize_round_brackets(value) for value in values if value]


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
    print(f"Wrote {len(resolved)} chapter files in both scripts.")


if __name__ == "__main__":
    main()
