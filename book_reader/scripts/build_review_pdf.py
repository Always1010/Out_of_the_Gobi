"""Create a smaller review copy without reflowing or rasterizing any text.

Only scans whose effective resolution exceeds 220 DPI are resampled. The
archival input is never overwritten; text, font programs, page geometry,
bookmarks, and links are verified after the review file has been saved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image

from export_common import OUTPUT


DEFAULT_DPI = 220
DEFAULT_QUALITY = 91


def _text_signature(page) -> list:
    """Exclude image data but retain every text span's geometry and styling."""
    result = []
    for block in page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            result.append((line["dir"], line["wmode"], [
                {key: value for key, value in span.items() if key not in {"chars"}}
                for span in line["spans"]
            ]))
    return result


def _links_signature(page) -> list:
    # Xref numbers are object identities, not link semantics; garbage
    # collection may renumber them while preserving all destinations.
    return [{key: value for key, value in link.items() if key not in {"xref", "id"}}
            for link in page.get_links()]


def _font_signature(document) -> set:
    fonts = set()
    seen = set()
    for page in document:
        for font in page.get_fonts(full=True):
            xref = font[0]
            if xref in seen:
                continue
            seen.add(xref)
            name, extension, kind, data = document.extract_font(xref)
            fonts.add((name, extension, kind, hashlib.sha256(data).hexdigest()))
    return fonts


def verify_review(source: Path, target: Path) -> dict:
    """Fail closed if anything except embedded raster data changed."""
    with fitz.open(source) as original, fitz.open(target) as review:
        assert len(original) == len(review), "Review page count changed"
        # Object-stream compression may upgrade the PDF container version.
        # All descriptive, provenance, and date metadata must stay unchanged.
        metadata = lambda doc: {key: value for key, value in doc.metadata.items() if key != "format"}
        assert metadata(original) == metadata(review), "Review metadata changed"
        assert original.get_toc() == review.get_toc(), "Review bookmarks changed"
        assert _font_signature(original) == _font_signature(review), "Embedded fonts changed"
        links = 0
        for index, (before, after) in enumerate(zip(original, review), 1):
            assert before.rect == after.rect, f"Page {index}: page size changed"
            assert before.mediabox == after.mediabox, f"Page {index}: media box changed"
            assert before.cropbox == after.cropbox, f"Page {index}: crop box changed"
            assert before.rotation == after.rotation, f"Page {index}: rotation changed"
            assert _text_signature(before) == _text_signature(after), f"Page {index}: text or text geometry changed"
            before_links, after_links = _links_signature(before), _links_signature(after)
            assert before_links == after_links, f"Page {index}: links changed"
            before_images = before.get_image_info()
            after_images = after.get_image_info()
            assert len(before_images) == len(after_images), f"Page {index}: image count changed"
            for old, new in zip(before_images, after_images):
                assert old["bbox"] == new["bbox"] and old["transform"] == new["transform"], \
                    f"Page {index}: image position changed"
            links += len(before_links)
        return {"pages": len(original), "bookmarks": len(original.get_toc()),
                "links": links, "text_fonts_positions_preserved": True}


def build_review_one(source: Path, target: Path | None = None, *,
                     dpi: float = DEFAULT_DPI, quality: int = DEFAULT_QUALITY) -> Path:
    source = Path(source)
    target = Path(target) if target else source.with_name(source.stem + "-审阅版.pdf")
    if source.resolve() == target.resolve():
        raise ValueError("The review copy must not overwrite the archival master")
    if not source.is_file():
        raise FileNotFoundError(source)
    if dpi <= 0 or not 1 <= quality <= 100:
        raise ValueError("DPI must be positive and JPEG quality must be between 1 and 100")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".building.pdf")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    changed = []
    with fitz.open(source) as document:
        uses: dict[int, list] = {}
        for page_index, page in enumerate(document):
            for info in page.get_image_info(xrefs=True):
                if info["xref"]:
                    uses.setdefault(info["xref"], []).append((page_index, info))
        for xref, occurrences in uses.items():
            first_page, first = occurrences[0]
            width, height = first["width"], first["height"]
            required_width = required_height = 0.0
            minimum_dpi = float("inf")
            for _, info in occurrences:
                a, b, c, d, _, _ = info["transform"]
                display_width, display_height = math.hypot(a, b), math.hypot(c, d)
                if display_width <= 0 or display_height <= 0:
                    continue
                required_width = max(required_width, display_width * dpi / 72)
                required_height = max(required_height, display_height * dpi / 72)
                minimum_dpi = min(minimum_dpi, width * 72 / display_width,
                                  height * 72 / display_height)
            if minimum_dpi <= dpi or required_width == 0 or required_height == 0:
                continue
            ratio = max(required_width / width, required_height / height)
            new_size = (min(width, math.ceil(width * ratio)), min(height, math.ceil(height * ratio)))
            if new_size == (width, height):
                continue
            extracted = document.extract_image(xref)
            # Soft masks carry transparency; leave them and their base images
            # alone instead of silently changing the page's compositing.
            if not extracted or extracted.get("smask", 0):
                continue
            with Image.open(BytesIO(extracted["image"])) as image:
                if image.mode not in {"L", "RGB"}:
                    image = image.convert("RGB")
                resized = image.resize(new_size, Image.Resampling.LANCZOS)
                stream = BytesIO()
                resized.save(stream, format="JPEG", quality=quality,
                             optimize=True, subsampling=0)
            jpeg = stream.getvalue()
            if len(jpeg) >= len(document.xref_stream_raw(xref)):
                continue
            document[first_page].replace_image(xref, stream=jpeg)
            changed.append({"source_xref": xref, "pages": sorted({p + 1 for p, _ in occurrences}),
                            "before_pixels": [width, height], "after_pixels": list(new_size),
                            "before_min_dpi": round(minimum_dpi, 3), "jpeg_quality": quality})
        document.save(temporary, garbage=4, deflate=True, deflate_fonts=True,
                      use_objstms=1, no_new_id=True)
    try:
        validation = verify_review(source, temporary)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash, "Archival master changed"
        temporary.replace(target)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    manifest = {
        "source": str(source), "target": str(target), "source_sha256": source_hash,
        "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "source_bytes": source.stat().st_size, "target_bytes": target.stat().st_size,
        "target_dpi": dpi, "jpeg_quality": quality, "changed_images": changed,
        "validation": validation,
    }
    target.with_suffix(".review.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", help="Archival PDF; otherwise select with --script")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--script", choices=["simplified", "traditional", "both"], default="both")
    parser.add_argument("--dpi", type=float, default=DEFAULT_DPI)
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    args = parser.parse_args()
    if args.source:
        sources = [args.source]
    else:
        scripts = [args.script] if args.script != "both" else ["simplified", "traditional"]
        sources = [OUTPUT / f"走出戈壁-{'简体' if script == 'simplified' else '繁体'}.pdf" for script in scripts]
    if args.output and len(sources) != 1:
        parser.error("--output requires a single source")
    for source in sources:
        print(build_review_one(source, args.output, dpi=args.dpi, quality=args.quality), flush=True)


if __name__ == "__main__":
    main()
