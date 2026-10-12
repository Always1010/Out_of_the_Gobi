"""Derive continuous manuscripts from the reviewed paginated source files.

Do not re-read OCR or retranslate vocabulary here: that would undo corrections.
Physical scan page markers stay in the source and are removed only in this
reading view. Explicitly reviewed joins are recorded in the correction manifest.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ocr_common import normalized
from proofreading import PAGE_RE, frontmatter_texts, read_manifest, rebuild_paginated_books

BOOK = Path(__file__).resolve().parents[1]
TEXT = BOOK / "text"
SENTENCE_ENDINGS = ("。", "！", "？", "；", "：", "…", ".", "!", "?", ";", ":", "”", "』", "」", "）", ")")


def ends_sentence(value: str) -> bool:
    return value.rstrip().endswith(SENTENCE_ENDINGS)


def is_chapter_heading(value: str, title: str) -> bool:
    value, title = value.replace("爲", "為"), title.replace("爲", "為")
    return normalized(value) in {normalized(title), normalized(title.split("：")[-1])} or bool(re.fullmatch(r"第[一二三四五六七八九十百零]+章", value))


def render_chapter(source: str, title: str, join_rules: list[dict]) -> str:
    forced_joins = {entry["page"] for entry in join_rules}
    end_markers = {entry["defer_image"] for entry in join_rules if entry.get("image_placement") == "chapter_end"}
    deferred_markers = {entry["defer_image"]: entry["page"] for entry in join_rules
                        if "defer_image" in entry and entry["defer_image"] not in end_markers}
    pending_images: list[str] = []
    end_images: list[str] = []
    blocks = [f"# {title}"]
    previous_text_index: int | None = None
    previous_page_had_image = False
    markers = list(PAGE_RE.finditer(source))
    for index, marker in enumerate(markers):
        page = int(marker.group(1))
        end = markers[index + 1].start() if index + 1 < len(markers) else len(source)
        body = source[marker.end():end]
        paragraphs = [value.strip() for value in re.split(r"\n\s*\n", body) if value.strip()]
        had_image = False
        for paragraph_index, value in enumerate(paragraphs):
            if is_chapter_heading(value, title):
                continue
            if value in end_markers:
                end_images.append(value)
                continue
            if value in deferred_markers:
                pending_images.append(value)
                continue
            if value == "★★★" or value.startswith("<!-- Image plate:"):
                blocks.append(value)
                previous_text_index = None
                had_image = value.startswith("<!-- Image plate:") or had_image
                continue
            can_join = (
                paragraph_index == 0 and previous_text_index is not None
                and not previous_page_had_image
                and (page in forced_joins or not ends_sentence(blocks[previous_text_index]))
            )
            if can_join:
                blocks[previous_text_index] += value
            else:
                blocks.append(value)
                previous_text_index = len(blocks) - 1
            if pending_images and page in forced_joins:
                blocks.extend(pending_images)
                pending_images.clear()
                previous_text_index = None
        previous_page_had_image = had_image
    assert not pending_images, "A relocated image did not find its reviewed paragraph join"
    assert set(end_images) == end_markers and len(end_images) == len(end_markers), "A chapter-end plate is missing or duplicated"
    blocks.extend(end_images)
    return "\n\n".join(blocks).rstrip() + "\n"


def main() -> None:
    chapters = json.loads((TEXT / "chapters.json").read_text(encoding="utf-8"))
    manifest = read_manifest()
    for script in ("traditional", "simplified"):
        output = TEXT / f"{script}-continuous"
        output.mkdir(parents=True, exist_ok=True)
        full_book = frontmatter_texts(script, False)
        for index, chapter in enumerate(chapters, 1):
            filename = f"{index:02d}-{chapter['id']}.md"
            source = (TEXT / script / filename).read_text(encoding="utf-8")
            joins = [
                entry for entry in manifest.get("continuous_joins", [])
                if entry["file"] == filename and script in entry.get("variants", ["traditional", "simplified"])
            ]
            rendered = render_chapter(source, chapter[f"title_{script}"], joins)
            (output / filename).write_text(rendered, encoding="utf-8")
            full_book.append(rendered.rstrip())
        (TEXT / f"book-{script}-continuous.md").write_text("\n\n---\n\n".join(full_book) + "\n\n---\n", encoding="utf-8")
        print(f"Wrote {len(chapters)} {script} sections from the reviewed paginated manuscripts.")
    rebuild_paginated_books()


if __name__ == "__main__":
    main()
