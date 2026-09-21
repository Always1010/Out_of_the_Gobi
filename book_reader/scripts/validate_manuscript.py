"""Check chapter ownership and synchronized manuscript variants."""

from __future__ import annotations

import json
import re
from pathlib import Path

from assemble_transcript import chinese_number, load_page, normalized, page_paragraphs, reading_paragraphs


BOOK = Path(__file__).resolve().parents[1]
TEXT = BOOK / "text"
VARIANTS = ("traditional", "simplified", "traditional-continuous", "simplified-continuous")


def validate() -> None:
    chapters = json.loads((TEXT / "chapters.json").read_text(encoding="utf-8"))
    image_pages = {entry["pdf_page"] for entry in json.loads((BOOK / "images" / "images.json").read_text(encoding="utf-8"))["pages"]}
    assert len(chapters) == 33, "Expected 33 sections"
    assert 352 not in image_pages and len(reading_paragraphs(352)) > 1, "PDF 352 is a text page"
    assert "★★★" in page_paragraphs(41) and "★★★" in page_paragraphs(81)
    starts = [item["pdf_page_start"] for item in chapters]
    assert starts == sorted(set(starts)), "Chapter start pages must increase"

    for chapter in chapters:
        if "number" not in chapter:
            continue
        page = chapter["pdf_page_start"]
        label = f"第{chinese_number(chapter['number'])}章"
        lines, _scores, polygons = load_page(page)
        assert any(
            normalized(line).startswith(label) and 330 <= polygon[0][1] <= 850
            for line, polygon in zip(lines, polygons)
        ), f"{chapter['id']} is assigned to a running header instead of its opening page {page}"

    for directory in VARIANTS:
        files = sorted((TEXT / directory).glob("*.md"))
        assert len(files) == len(chapters), f"{directory}: missing section files"
        contents = [path.read_text(encoding="utf-8") for path in files]
        for index, chapter in enumerate(chapters):
            assert files[index].name == f"{index + 1:02d}-{chapter['id']}.md"
            assert contents[index].startswith("# ")
            if index == 0 or "number" not in chapter:
                continue
            label = f"第{chinese_number(chapter['number'])}章"
            assert not re.search(rf"(?m)^{label}$", contents[index - 1]), (
                f"{chapter['id']} opening is still in the previous {directory} file"
            )
            if "continuous" not in directory:
                assert f"<!-- PDF {chapter['pdf_page_start']} -->" in contents[index]
                assert f"<!-- PDF {chapter['pdf_page_start']} -->" not in contents[index - 1]
        if "continuous" in directory:
            assert all("<!-- PDF " not in content for content in contents)
        else:
            assert all("<!-- PDF " in content for content in contents)
        assert all(
            line.strip() == "★★★"
            for content in contents for line in content.splitlines() if "★" in line
        ), f"{directory}: nonstandard scene separator"

    simplified = "\n".join(
        path.read_text(encoding="utf-8")
        for directory in ("simplified", "simplified-continuous")
        for path in (TEXT / directory).glob("*.md")
    )
    assert not any(char in simplified for char in "牠衞簷敍擡")
    assert "費羅" in (TEXT / "traditional-continuous" / "29-chapter-26.md").read_text(encoding="utf-8")
    print("Validated 33 chapter starts and all four manuscript variants.")


if __name__ == "__main__":
    validate()
