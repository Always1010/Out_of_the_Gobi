"""Resolve verified book fonts and embed the small subsets used by readers.

Builds never download fonts implicitly. Prepare the pinned upstream fonts with
build-ebooks.yml, or supply equivalent local files using the documented paths.
"""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Iterable

from fontTools import subset
from fontTools.ttLib import TTFont


FONT_LICENSES = Path(__file__).resolve().parents[1] / "fonts"
ROLES = {
    "number": ("GobiChapterNumber", "chapter-numbers.ttf", 400),
    "title": ("GobiChapterTitle", "chapter-titles.ttf", 400),
    "lead-in": ("GobiLeadIn", "lead-ins.ttf", 300),
}


def font_path(script: str, role: str = "number") -> Path:
    """Find the precise family for a role; never silently substitute a font."""
    if script not in {"simplified", "traditional"}:
        raise ValueError(script)
    if role not in ROLES:
        raise ValueError(role)
    suffix = "SC" if script == "simplified" else "TC"
    override_key = {"number": "GOBI_FONT", "title": "GOBI_SERIF", "lead-in": "GOBI_LEADIN"}[role] + "_" + suffix
    override = os.environ.get(override_key)
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Configured {role} font not found: {path}")
        return path
    filename = {
        "number": f"NotoSans{suffix}-Regular.ttf",
        "title": f"NotoSerif{suffix}-Regular.ttf",
        "lead-in": "LXGWWenKai-Light.ttf",
    }[role]
    directories = []
    main_font = os.environ.get(f"GOBI_FONT_{suffix}")
    if main_font:
        directories.append(Path(main_font).expanduser().parent)
    directories.extend([
        FONT_LICENSES,
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/share/fonts/truetype/lxgw"),
        Path.home() / ".local/share/fonts",
    ])
    for directory in directories:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Missing {filename} for {script} {role}; prepare the verified book fonts "
        f"beside GOBI_FONT_{suffix}, or set {override_key}."
    )


def font_css() -> str:
    """The same family names are shared by EPUB and the offline reader."""
    return "\n".join(
        f'@font-face {{ font-family: "{family}"; src: url("fonts/{filename}") format("truetype"); '
        f'font-weight: {weight}; font-style: normal; font-display: swap; }}'
        for family, filename, weight in ROLES.values()
    ) + "\n"


def subset_font(script: str, role: str, text: str) -> bytes:
    """Subset by actual rendered text, retaining searchable Unicode mappings."""
    source = font_path(script, role)
    font = TTFont(source, recalcTimestamp=False)
    try:
        if "fvar" in font:
            raise ValueError(f"Instantiate variable font at its intended weight before embedding: {source}")
        characters = {ord(char) for char in text if not char.isspace()}
        missing = characters - set(font.getBestCmap())
        if missing:
            rendered = " ".join(f"U+{code:04X} ({chr(code)})" for code in sorted(missing))
            raise ValueError(f"{source.name} does not cover {role} text: {rendered}")
        options = subset.Options()
        options.notdef_glyph = True
        options.notdef_outline = True
        options.recommended_glyphs = True
        options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14, 16, 17]
        options.name_languages = ["*"]
        options.name_legacy = True
        options.recalc_timestamp = False
        worker = subset.Subsetter(options=options)
        worker.populate(text=text + " \u3000")
        worker.subset(font)
        buffer = BytesIO()
        font.save(buffer)
        return buffer.getvalue()
    finally:
        font.close()


def font_assets(script: str, chapters: Iterable, frontmatter: Iterable) -> dict[str, bytes]:
    """Return filenames relative to the export's fonts directory, plus licenses."""
    chapters = list(chapters)
    frontmatter = list(frontmatter)
    texts = {
        "number": "".join(chapter.number_label for chapter in chapters),
        "title": "目录目錄走出戈壁：我的中美故事" + "".join(part.title for part in [*frontmatter, *chapters]),
        "lead-in": "".join(block.value for chapter in chapters for block in chapter.blocks if block.role == "lead-in"),
    }
    assets = {
        ROLES[role][1]: subset_font(script, role, text)
        for role, text in texts.items()
    }
    for filename in ("Noto-OFL.txt", "LXGWWenKai-OFL.txt"):
        assets[filename] = (FONT_LICENSES / filename).read_bytes()
    return assets
