"""Apply reviewed, page-scoped corrections without changing the OCR evidence.

The two paginated manuscripts remain authoritative. Each manifest replacement
is exact and guarded by the scan page, manuscript variant and expected count.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

BOOK = Path(__file__).resolve().parents[1]
TEXT = BOOK / "text"
MANIFEST = BOOK / "qa" / "proofreading-corrections.json"
PAGE_RE = re.compile(r"(?m)^<!-- PDF (\d+) -->\n")


def read_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"patches": [], "continuous_joins": []}


def page_span(text: str, pages: list[int]) -> tuple[int, int]:
    markers = list(PAGE_RE.finditer(text))
    found = {int(match.group(1)): index for index, match in enumerate(markers)}
    if not pages or any(page not in found for page in pages):
        raise ValueError(f"Missing source page marker: {pages}")
    first, last = min(found[page] for page in pages), max(found[page] for page in pages)
    return markers[first].end(), markers[last + 1].start() if last + 1 < len(markers) else len(text)


def apply_patches() -> int:
    manifest = read_manifest()
    contents: dict[Path, str] = {}
    reviewed = {TEXT / relative for relative, expected in manifest.get("source_sha256", {}).items()
                if (TEXT / relative).is_file() and hashlib.sha256((TEXT / relative).read_bytes()).hexdigest() == expected}
    applied = 0
    for patch in manifest["patches"]:
        path = TEXT / patch["variant"] / patch["file"]
        if path in reviewed:
            continue
        text = contents.get(path, path.read_text(encoding="utf-8"))
        start, end = page_span(text, patch["pages"])
        section = text[start:end]
        before, after = patch["before"], patch["after"]
        expected = patch.get("count", 1)
        actual = section.count(before)
        if before in after and section.count(after) == expected:
            pass  # Insertion whose source remains inside its reviewed result.
        elif actual == expected:
            section = section.replace(before, after)
            text = text[:start] + section + text[end:]
            applied += 1
        elif actual == 0 and (not after or section.count(after) == expected):
            pass  # Safe re-run on the already-reviewed source.
        else:
            raise ValueError(f"{patch['id']} {path.name} {patch['variant']} pages {patch['pages']}: expected {expected} matches, found {actual}")
        contents[path] = text
    for path, text in contents.items():
        path.write_text(text, encoding="utf-8")
    rebuild_paginated_books()
    return applied


def frontmatter_texts(script: str, paginated: bool) -> list[str]:
    manifest = TEXT / "frontmatter.json"
    if not manifest.exists():
        return []
    data = json.loads(manifest.read_text(encoding="utf-8"))
    entries = data if isinstance(data, list) else data["sections"]
    result = []
    for entry in entries:
        path = TEXT / "frontmatter" / script / f"{entry['id']}.md"
        text = path.read_text(encoding="utf-8").rstrip()
        if paginated:
            lines = text.splitlines()
            lines.insert(1, f"\n<!-- PDF {entry['pdf_page']} -->")
            text = "\n".join(lines)
        result.append(text)
    return result


def rebuild_paginated_books() -> None:
    for script in ("traditional", "simplified"):
        parts = frontmatter_texts(script, True)
        parts.extend(path.read_text(encoding="utf-8").rstrip() for path in sorted((TEXT / script).glob("*.md")))
        (TEXT / f"book-{script}.md").write_text("\n\n---\n\n".join(parts) + "\n\n---\n", encoding="utf-8")


if __name__ == "__main__":
    print(f"Applied {apply_patches()} reviewed manuscript replacements.")
