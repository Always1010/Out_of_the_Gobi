"""Shared, read-only book data for EPUB and typeset PDF exports."""

from __future__ import annotations

import json
import os
import re
import subprocess
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


def load_chapters(script: str) -> list[Chapter]:
    if script not in {"simplified", "traditional"}:
        raise ValueError(script)
    manifest = json.loads((TEXT / "chapters.json").read_text(encoding="utf-8"))
    chapters: list[Chapter] = []
    for index, entry in enumerate(manifest, 1):
        path = TEXT / f"{script}-continuous" / f"{index:02d}-{entry['id']}.md"
        title = entry[f"title_{script}"]
        lines = path.read_text(encoding="utf-8").splitlines()
        blocks: list[Block] = []
        paragraph: list[str] = []

        def flush() -> None:
            value = "".join(part.strip() for part in paragraph).strip()
            paragraph.clear()
            if not value or value == title or CHAPTER_NUMBER_RE.fullmatch(value):
                return
            blocks.append(Block("break" if value == "★★★" else "paragraph", value))

        for raw in lines:
            line = raw.strip()
            image = IMAGE_RE.fullmatch(line)
            if image:
                flush()
                blocks.append(Block("image", image.group(1)))
            elif not line or line == "---" or line.startswith("# "):
                flush()
            else:
                paragraph.append(raw)
        flush()
        chapters.append(Chapter(entry["id"], title, tuple(blocks)))
    return chapters


def load_captions(script: str) -> dict[int, list[str]]:
    pages = json.loads((BOOK / "images" / "captions.json").read_text(encoding="utf-8"))["pages"]
    if script == "traditional":
        return {int(page): values for page, values in pages.items()}
    if script != "simplified":
        raise ValueError(script)
    # Match the mainland character choices already used by the reader site.
    try:
        from opencc import OpenCC
        from assemble_transcript import to_mainland_simplified
    except ModuleNotFoundError:
        # The bundled PDF runtime has ReportLab but not OpenCC; use the project's
        # existing OCR environment for exactly the same conversion as the site.
        converter_python = BOOK.parent / ".venv-ocr" / "Scripts" / "python.exe"
        if not converter_python.is_file():
            raise RuntimeError("OpenCC is needed for Simplified Chinese captions") from None
        result = subprocess.run(
            [str(converter_python), "-c", "import json; from export_common import load_captions; print(json.dumps(load_captions('simplified'), ensure_ascii=False))"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=True,
        )
        return {int(page): values for page, values in json.loads(result.stdout).items()}

    converter = OpenCC("tw2sp")
    return {
        int(page): [to_mainland_simplified(value, converter) for value in values]
        for page, values in pages.items()
    }


def image_pages(chapters: list[Chapter]) -> set[int]:
    return {int(block.value[5:8]) for chapter in chapters for block in chapter.blocks if block.kind == "image"}
