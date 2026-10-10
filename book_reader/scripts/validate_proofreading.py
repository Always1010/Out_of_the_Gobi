"""Regression checks for the original-scan correction decisions and derivations."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from build_continuous_transcript import render_chapter
from proofreading import TEXT, frontmatter_texts, page_span, read_manifest


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"<!--.*?-->", "", value, flags=re.S))


def validate() -> None:
    data = read_manifest()
    dispositions = {entry["id"]: entry for entry in data["dispositions"]}
    assert sum(key.startswith("R") for key in dispositions) == 544
    assert sum(key.startswith("N") for key in dispositions) == 24
    assert sum(key.startswith("C") for key in dispositions) == 11
    corrected = {key for patch in data["patches"] for key in patch.get("ids", [patch["id"]])}
    corrected.update(entry["id"] for entry in data.get("continuous_joins", []))
    corrected.update(data.get("metadata_corrections", []))
    required = {key for key, value in dispositions.items() if value["verification_status"] == "confirmed_transcription_error"}
    assert required <= corrected, f"Missing confirmed corrections: {sorted(required - corrected)}"
    for relative, expected in data.get("source_sha256", {}).items():
        actual = hashlib.sha256((TEXT / relative).read_bytes()).hexdigest()
        assert actual == expected, f"Reviewed source changed: {relative}"
    for entry in data["preserved_text"]:
        text = (TEXT / entry["variant"] / entry["file"]).read_text(encoding="utf-8")
        start, end = page_span(text, entry["pages"])
        assert normalized_text(entry["text"]) in normalized_text(text[start:end]), f"Original wording changed: {entry['id']}"
    chapter_manifest = json.loads((TEXT / "chapters.json").read_text(encoding="utf-8"))
    for script in ("traditional", "simplified"):
        for index, chapter in enumerate(chapter_manifest, 1):
            filename = f"{index:02d}-{chapter['id']}.md"
            paginated = (TEXT / script / filename).read_text(encoding="utf-8")
            continuous = (TEXT / f"{script}-continuous" / filename).read_text(encoding="utf-8")
            joins = [entry for entry in data["continuous_joins"] if entry["file"] == filename]
            expected = render_chapter(paginated, chapter[f"title_{script}"], joins)
            assert expected == continuous, f"Stale continuous source: {script}/{filename}"
        for continuous in (False, True):
            directory = f"{script}-continuous" if continuous else script
            parts = frontmatter_texts(script, not continuous)
            parts.extend(path.read_text(encoding="utf-8").rstrip() for path in sorted((TEXT / directory).glob("*.md")))
            expected = "\n\n---\n\n".join(parts) + "\n\n---\n"
            assert (TEXT / f"book-{directory}.md").read_text(encoding="utf-8") == expected, f"Stale compilation: {directory}"
    for script in ("simplified", "traditional"):
        content = (TEXT / f"book-{script}-continuous.md").read_text(encoding="utf-8")
        assert "978-988-74175-8-3" not in content
        assert "1904年至1905的日俄" in content
        assert "曲折又漫" in content and "·  \n" in content
        assert "<!-- Image plate: images/pages/page-350.jpg -->" in content
    print(f"Validated {len(required)} confirmed correction records, {len(data['preserved_text'])} original-wording checks, all source hashes, continuous views and four compilations.")


if __name__ == "__main__":
    validate()
