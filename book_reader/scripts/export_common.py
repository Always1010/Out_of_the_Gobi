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
    role: str = "body"
    alignment: str = "left"


@dataclass(frozen=True)
class Chapter:
    slug: str
    title: str
    blocks: tuple[Block, ...]
    number: int | None = None

    @property
    def number_label(self) -> str:
        return chapter_number(self.number)

    @property
    def label(self) -> str:
        return f"{self.number_label}　{self.title}" if self.number else self.title


def chapter_number(number: int | None) -> str:
    if number is None:
        return ""
    if not 1 <= number <= 29:
        raise ValueError(f"Unknown chapter number: {number}")
    digits = "零一二三四五六七八九"
    value = digits[number] if number < 10 else ("十" if number < 20 else "二十") + (digits[number % 10] if number % 10 else "")
    return f"第{value}章"


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
        if value and value.replace("爲", "為") != title.replace("爲", "為") and not CHAPTER_NUMBER_RE.fullmatch(value):
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


def with_lead_ins(blocks: tuple[Block, ...], slug: str, script: str) -> tuple[Block, ...]:
    entries = json.loads((TEXT / "lead-ins.json").read_text(encoding="utf-8"))["sections"]
    entry = next((entry for entry in entries if entry["id"] == slug), None)
    if entry is None:
        return blocks
    evidence = entry["scripts"][script]
    count = evidence["paragraph_count"]
    lead = blocks[:count]
    if not (all(block.kind == "paragraph" for block in lead)
            and blocks[count].kind == "break"
            and lead[0].value.startswith(evidence["start"])
            and lead[-1].value.endswith(evidence["end"])
            and blocks[count + 1].value.startswith(evidence["following"])):
        raise ValueError(f"Reviewed lead-in boundaries changed: {script}/{slug}")
    return tuple(Block(block.kind, block.value, "lead-in" if index < count else "body", block.alignment)
                 for index, block in enumerate(blocks))


def apply_line_layout(blocks: tuple[Block, ...], entries: list[dict], slug: str, script: str,
                      kind: str) -> tuple[Block, ...]:
    """Split only scan-reviewed line blocks; preserve every non-whitespace character.

    OCR paragraph and physical-page boundaries are not reliable semantic boundaries.
    Each exact, unique range may span adjacent paragraphs with the same role,
    but cannot cross an image, scene break, or another semantic block.
    """
    original = "".join(re.sub(r"\s+", "", block.value) for block in blocks)
    for entry in entries:
        if entry["chapter"] != slug:
            continue
        verse = "\n".join(entry[f"lines_{script}"])
        needle = re.sub(r"\s+", "", verse)
        allowed = {"left", "center"} if kind == "verse" else {"right"}
        if kind not in {"verse", "signature"} or not needle or entry["alignment"] not in allowed:
            raise ValueError(f"Invalid {kind} layout: {entry['id']}")
        matches = []
        index = 0
        while index < len(blocks):
            if blocks[index].kind != "paragraph":
                index += 1
                continue
            end = index + 1
            while end < len(blocks) and blocks[end].kind == "paragraph" and blocks[end].role == blocks[index].role:
                end += 1
            offsets = [(i, j) for i in range(index, end)
                       for j, char in enumerate(blocks[i].value) if not char.isspace()]
            haystack = "".join(blocks[i].value[j] for i, j in offsets)
            start = haystack.find(needle)
            while start != -1:
                matches.append((offsets[start], offsets[start + len(needle) - 1]))
                start = haystack.find(needle, start + 1)
            index = end
        if len(matches) != 1:
            raise ValueError(f"Reviewed {kind} must match exactly once: {script}/{entry['id']} ({len(matches)})")
        (first, start), (last, end) = matches[0]
        role = blocks[first].role
        before, after = blocks[first].value[:start].strip(), blocks[last].value[end + 1:].strip()
        replacement = ([Block("paragraph", before, role)] if before else [])
        replacement += [Block(kind, verse, role, entry["alignment"])]
        replacement += [Block("paragraph", after, role)] if after else []
        blocks = blocks[:first] + tuple(replacement) + blocks[last + 1:]
    if original != "".join(re.sub(r"\s+", "", block.value) for block in blocks):
        raise ValueError(f"{kind} layout changed source text: {script}/{slug}")
    return blocks


def apply_verse_layout(blocks: tuple[Block, ...], entries: list[dict], slug: str, script: str) -> tuple[Block, ...]:
    return apply_line_layout(blocks, entries, slug, script, "verse")


def with_signature_layout(blocks: tuple[Block, ...], slug: str, script: str) -> tuple[Block, ...]:
    entries = json.loads((TEXT / "signature-layout.json").read_text(encoding="utf-8"))["signatures"]
    return apply_line_layout(blocks, entries, slug, script, "signature")


def with_verse_layout(blocks: tuple[Block, ...], slug: str, script: str) -> tuple[Block, ...]:
    entries = json.loads((TEXT / "verse-layout.json").read_text(encoding="utf-8"))["verses"]
    return apply_verse_layout(blocks, entries, slug, script)


def load_chapters(script: str) -> list[Chapter]:
    if script not in {"simplified", "traditional"}:
        raise ValueError(script)
    manifest = json.loads((TEXT / "chapters.json").read_text(encoding="utf-8"))
    return [
        Chapter(entry["id"], entry[f"title_{script}"], with_signature_layout(with_verse_layout(with_lead_ins(parse_blocks(
            (TEXT / f"{script}-continuous" / f"{index:02d}-{entry['id']}.md").read_text(encoding="utf-8"),
            entry[f"title_{script}"],
        ), entry["id"], script), entry["id"], script), entry["id"], script), entry.get("number"))
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
