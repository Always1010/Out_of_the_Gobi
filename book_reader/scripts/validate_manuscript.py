"""Check chapter ownership and synchronized manuscript variants."""

from __future__ import annotations

import json
import re
import argparse
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from assemble_transcript import chinese_number, load_page, normalized, page_paragraphs, reading_paragraphs
from export_common import OUTPUT, expected_body_image_pages, image_pages, load_captions, load_chapters, load_frontmatter, parse_blocks


BOOK = Path(__file__).resolve().parents[1]
TEXT = BOOK / "text"
VARIANTS = ("traditional", "simplified", "traditional-continuous", "simplified-continuous")


def validate_frontmatter() -> None:
    for script in ("traditional", "simplified"):
        front = load_frontmatter(script)
        assert [part.slug for part in front] == ["author-biography", "dedication"]
        assert [part.source_page for part in front] == [4, 5], "Copyright/version page must remain omitted"
        assert len(front[0].blocks) == 7, "The author biography has seven paragraphs"
        assert [part.presentation for part in front] == ["text", "scan"]
        assert all(block.kind == "paragraph" for part in front for block in part.blocks)
        expected = ("獻給患難與共的戰友\n和我們充滿希望的後代" if script == "traditional"
                    else "献给患难与共的战友\n和我们充满希望的后代")
        assert len(front[1].blocks) == 1 and front[1].blocks[0].value == expected
    assert parse_blocks("# 測試\n\n甲  \n乙\n丙\n", "測試")[0].value == "甲\n乙丙"


def validate_exports() -> None:
    """Check exported structure, search text, source omission and PDF numbering."""
    import fitz
    opf_ns = {"o": "http://www.idpf.org/2007/opf"}
    for script, label in (("simplified", "简体"), ("traditional", "繁体")):
        front = load_frontmatter(script)
        chapters = load_chapters(script)
        assert image_pages(chapters) == expected_body_image_pages(), "Body image plates do not match the source manifest"
        assert sum(block.kind == "image" for chapter in chapters for block in chapter.blocks) == len(expected_body_image_pages()), "A body plate is duplicated"
        with zipfile.ZipFile(OUTPUT / f"走出戈壁-{label}.epub") as archive:
            assert archive.namelist()[0] == "mimetype" and archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
            assert archive.read("mimetype") == b"application/epub+zip"
            assert not any("page-003" in name for name in archive.namelist())
            package = ET.fromstring(archive.read("OEBPS/content.opf"))
            manifest = {item.attrib["id"]: item.attrib["href"] for item in package.findall("o:manifest/o:item", opf_ns)}
            spine = [item.attrib["idref"] for item in package.findall("o:spine/o:itemref", opf_ns)]
            assert spine == ["cover-page", "title-page", "front-author-biography", "front-dedication", "nav"] + [f"chapter-{i:02d}" for i in range(1, 34)]
            assert all("OEBPS/" + href in archive.namelist() for href in manifest.values())
            for index, section in enumerate([*front, *chapters]):
                filename = f"front-{section.slug}.xhtml" if index < 2 else f"chapter-{index - 1:02d}.xhtml"
                document = ET.fromstring(archive.read("OEBPS/" + filename))
                visible = "".join(document.itertext())
                for block in section.blocks:
                    if block.kind == "paragraph":
                        assert block.value.replace("\n", "") in visible, f"EPUB stale or missing text: {filename}"
            assert archive.testzip() is None
        with fitz.open(OUTPUT / f"走出戈壁-{label}.pdf") as pdf:
            assert len(pdf.get_toc()) == 35, "PDF should bookmark two front-matter sections and 33 chapters"
            # Ignore only our bottom page-number area when testing paragraphs
            # that flow across physical pages. All manuscript text and captions
            # must survive typesetting, including explicit verse line breaks.
            searchable_book = re.sub(r"\s+", "", "".join(
                page.get_text(clip=fitz.Rect(0, 0, page.rect.width, page.rect.height - 39)) for page in pdf
            ))
            for section in [*front, *chapters]:
                for block in section.blocks:
                    if block.kind == "paragraph":
                        assert re.sub(r"\s+", "", block.value) in searchable_book, f"PDF stale or missing text: {section.slug}"
            for values in load_captions(script).values():
                for value in values:
                    assert re.sub(r"\s+", "", value) in searchable_book, f"PDF missing caption: {value[:40]}"
            for number, page in enumerate(pdf, 1):
                footer = page.get_textbox(fitz.Rect(0, page.rect.height - 37, page.rect.width, page.rect.height)).strip()
                assert footer == str(number), f"Nonconsecutive reading page: {number}: {footer!r}"
            for offset, section in enumerate(front, 2):
                searchable = re.sub(r"\s+", "", pdf[offset].get_text())
                for block in section.blocks:
                    assert re.sub(r"\s+", "", block.value) in searchable, f"Missing PDF front-matter text: {section.slug}"
                assert bool(pdf[offset].get_images()) == (section.presentation == "scan"), "Only scan-presented front matter embeds its page image"
            assert [item[1] for item in pdf.get_toc()] == [part.title for part in front] + [chapter.label for chapter in chapters]
            picture_pages = [page for page in list(pdf)[4:] if page.get_images()]
            plates = [block for chapter in chapters for block in chapter.blocks if block.kind == "image"]
            assert len(picture_pages) == len(plates) == 20, "Each body plate must occupy its own page"
            captions = load_captions(script)
            for page, block in zip(picture_pages, plates):
                actual = re.sub(r"\s+", "", page.get_text(clip=fitz.Rect(0, 0, page.rect.width, page.rect.height - 39)))
                expected = re.sub(r"\s+", "", "".join(captions.get(int(block.value[5:8]), [])))
                assert actual == expected, f"Prose shares image page or caption misplaced: {block.value}"
    site = BOOK / "site" / "dist"
    payload = (site / "data.js").read_text(encoding="utf-8").split("=", 1)[1].strip().removesuffix(";")
    sections = json.loads(payload)["chapters"]
    assert [section["id"] for section in sections] == ["front-author-biography", "front-dedication"] + [f"section-{i:02d}" for i in range(1, 34)]
    assert not (site / "images" / "page-003.png").exists()
    for section in sections:
        for asset in re.findall(r'<img[^>]+src="([^"]+)"', section["html"]):
            assert (site / asset).is_file(), f"Missing offline asset: {asset}"
    assert sections[0]["searchText"] and '<img ' not in sections[0]["html"]
    assert sections[1]["searchText"] and '<img ' in sections[1]["html"]
    print("Validated both EPUB/PDF exports, consecutive PDF numbering and offline front matter.")


def validate() -> None:
    validate_frontmatter()
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
        for content in contents:
            assert "(" not in content and ")" not in content, f"{directory}: halfwidth round bracket"
            balance = 0
            for character in content:
                if character == "（":
                    balance += 1
                elif character == "）":
                    balance -= 1
                assert balance >= 0, f"{directory}: unmatched closing round bracket"
            assert balance == 0, f"{directory}: unmatched opening round bracket"

    simplified = "\n".join(
        path.read_text(encoding="utf-8")
        for directory in ("simplified", "simplified-continuous")
        for path in (TEXT / directory).glob("*.md")
    )
    assert not any(char in simplified for char in "牠衞簷敍擡")
    assert "費羅" in (TEXT / "traditional-continuous" / "29-chapter-26.md").read_text(encoding="utf-8")
    print("Validated 33 chapter starts, all four manuscript variants and two front-matter sections.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exports", action="store_true", help="also validate freshly built EPUB, PDF and offline reader outputs")
    args = parser.parse_args()
    validate()
    if args.exports:
        validate_exports()
