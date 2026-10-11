"""Shared, read-only book data for EPUB, typeset PDF and offline exports."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path

BOOK = Path(__file__).resolve().parents[1]
TEXT = BOOK / "text"
IMAGES = BOOK / "images" / "pages"
OUTPUT = BOOK / "output"
IMAGE_RE = re.compile(r"<!-- Image plate: images/pages/(page-\d{3}\.jpg) -->")
CHAPTER_NUMBER_RE = re.compile(r"第[一二三四五六七八九十百]+章")


@dataclass(frozen=True)
class Block:
    kind: str
    value: str


@dataclass(frozen=True)
class Chapter:
    slug: str
    title: str
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class FrontMatter:
    slug: str
    title: str
    source_page: int
    image: Path
    layout: str
    presentation: str
    blocks: tuple[Block, ...]


def paragraph_text(lines: list[str]) -> str:
    """Join ordinary OCR wraps but retain explicit Markdown hard line breaks."""
    return "".join(line.strip() + ("\n" if line.endswith("  ") else "") for line in lines).strip()


def parse_blocks(markdown: str, title: str) -> tuple[Block, ...]:
    blocks: list[Block] = []
    paragraph: list[str] = []

    def flush() -> None:
        value = paragraph_text(paragraph)
        paragraph.clear()
        if value and value != title and not CHAPTER_NUMBER_RE.fullmatch(value):
            blocks.append(Block("break" if value == "★★★" else "paragraph", value))

    for raw in markdown.splitlines():
        line = raw.strip()
        image = IMAGE_RE.fullmatch(line)
        if image:
            flush()
            blocks.append(Block("image", image.group(1)))
        elif not line or line == "---" or line.startswith("# "):
            flush()
        elif line.startswith("<!--"):
            flush()
        else:
            paragraph.append(raw)
    flush()
    return tuple(blocks)


def load_chapters(script: str) -> list[Chapter]:
    if script not in {"simplified", "traditional"}:
        raise ValueError(script)
    manifest = json.loads((TEXT / "chapters.json").read_text(encoding="utf-8"))
    return [
        Chapter(entry["id"], entry[f"title_{script}"], parse_blocks(
            (TEXT / f"{script}-continuous" / f"{index:02d}-{entry['id']}.md").read_text(encoding="utf-8"),
            entry[f"title_{script}"],
        ))
        for index, entry in enumerate(manifest, 1)
    ]


def load_frontmatter(script: str) -> list[FrontMatter]:
    """Independent front matter preserves the existing 33 chapter identities."""
    if script not in {"simplified", "traditional"}:
        raise ValueError(script)
    manifest = json.loads((TEXT / "frontmatter.json").read_text(encoding="utf-8"))
    result = []
    for entry in manifest:
        title = entry[f"title_{script}"]
        source = TEXT / "frontmatter" / script / f"{entry['id']}.md"
        picture = BOOK / "images" / entry["asset"]
        if not picture.is_file():
            raise FileNotFoundError(picture)
        presentation = entry["presentation"]
        if presentation not in {"text", "scan"}:
            raise ValueError(f"Unknown front-matter presentation: {presentation}")
        result.append(FrontMatter(entry["id"], title, int(entry["pdf_page"]), picture,
                                  entry["layout"], presentation, parse_blocks(source.read_text(encoding="utf-8"), title)))
    return result


def load_captions(script: str) -> dict[int, list[str]]:
    pages = json.loads((BOOK / "images" / "captions.json").read_text(encoding="utf-8"))["pages"]
    for source, destinations in reading_layout()["caption_distribution"].items():
        values = pages.pop(source)
        indices = [index for selected in destinations.values() for index in selected]
        if sorted(indices) != list(range(len(values))):
            raise ValueError(f"Caption allocation loses or duplicates text: {source}")
        for target, selected in destinations.items():
            if target in pages:
                raise ValueError(f"Caption allocation overwrites an existing page: {target}")
            pages[target] = [values[index] for index in selected]
    if script == "traditional":
        return {int(page): values for page, values in pages.items()}
    if script != "simplified":
        raise ValueError(script)
    try:
        from opencc import OpenCC
    except ModuleNotFoundError:
        raise RuntimeError("Install opencc-python-reimplemented to build Simplified Chinese captions") from None
    # Convert character forms only. Regional phrase conversion (tw2sp) can
    # silently replace an author's words, including 資料, 文件 and 影片.
    converter = OpenCC("t2s")
    return {int(page): [converter.convert(value) for value in values] for page, values in pages.items()}


def reading_layout() -> dict:
    return json.loads((BOOK / "images" / "reading-layout.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def reading_image(filename: str) -> Path:
    source = IMAGES / filename
    crop = reading_layout()["crops"].get(filename)
    if crop is None:
        return source
    from PIL import Image
    destination = OUTPUT / "reading-images" / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        if list(image.size) != crop["source_size"]:
            raise ValueError(f"Reviewed crop coordinates no longer match: {source}")
        image.crop(tuple(crop["box"])).save(destination, quality=95, optimize=True)
    return destination


def image_pages(chapters: list[Chapter]) -> set[int]:
    return {int(block.value[5:8]) for chapter in chapters for block in chapter.blocks if block.kind == "image"}


def expected_body_image_pages() -> set[int]:
    manifest = json.loads((BOOK / "images" / "images.json").read_text(encoding="utf-8"))
    return {int(entry["pdf_page"]) for entry in manifest["pages"] if int(entry["pdf_page"]) not in {1, 2}}
