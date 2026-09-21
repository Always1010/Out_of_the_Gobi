"""Render and OCR the source PDF one page at a time with resume support."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / "book_reader"
PDF = ROOT / "走出戈壁-单伟健.pdf"
PILOT = ROOT / "pilot20" / "ocr" / "paddle_small"
OCR_DIR = BOOK / "ocr" / "paddle_small"
TEXT_DIR = BOOK / "ocr" / "pages"
INDEX_PATH = BOOK / "ocr" / "pages.json"
PAGES = 420


def parse_pages(spec: str) -> list[int]:
    pages: set[int] = set()
    for part in spec.split(","):
        bounds = [int(value) for value in part.split("-")]
        if len(bounds) == 1:
            pages.add(bounds[0])
        elif len(bounds) == 2:
            pages.update(range(bounds[0], bounds[1] + 1))
        else:
            raise ValueError(f"Invalid page range: {part}")
    invalid = [page for page in pages if not 1 <= page <= PAGES]
    if invalid:
        raise ValueError(f"Page outside 1-{PAGES}: {invalid}")
    return sorted(pages)


def import_pilot(page: int) -> bool:
    source = PILOT / f"page-{page:03d}.json"
    target = OCR_DIR / source.name
    if page <= 20 and source.exists() and not target.exists():
        shutil.copy2(source, target)
        return True
    return False


def write_text_and_index() -> None:
    entries = []
    for page in range(1, PAGES + 1):
        path = OCR_DIR / f"page-{page:03d}.json"
        status = "complete" if path.exists() else "pending"
        entry: dict[str, object] = {"pdf_page": page, "status": status}
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = payload["res"]
            lines = result.get("rec_texts", [])
            scores = result.get("rec_scores", [])
            (TEXT_DIR / f"page-{page:03d}.txt").write_text(
                "\n".join(lines).strip() + "\n", encoding="utf-8"
            )
            entry.update(
                {
                    "line_count": len(lines),
                    "character_count": len("".join(lines)),
                    "mean_line_confidence": round(statistics.mean(scores), 3) if scores else None,
                    **payload.get("book_reader_meta", payload.get("pilot_meta", {})),
                }
            )
        entries.append(entry)
    INDEX_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", default=f"1-{PAGES}")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not PDF.exists():
        raise FileNotFoundError(PDF)
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    requested = parse_pages(args.pages)
    for page in requested:
        import_pilot(page)
    missing = [
        page
        for page in requested
        if args.force or not (OCR_DIR / f"page-{page:03d}.json").exists()
    ]
    if not missing:
        write_text_and_index()
        print("All requested pages already exist.")
        return

    cache = Path(tempfile.gettempdir()) / "gobi-paddle-models"
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(cache)
    os.environ["HF_HOME"] = str(cache)
    os.environ.setdefault("OMP_NUM_THREADS", "4")

    from paddleocr import PaddleOCR

    ocr = PaddleOCR(
        text_detection_model_name="PP-OCRv6_small_det",
        text_recognition_model_name="PP-OCRv6_small_rec",
        device="cpu",
        enable_mkldnn=False,
        cpu_threads=4,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    with tempfile.TemporaryDirectory(prefix="gobi-ocr-") as temporary:
        temp = Path(temporary)
        for index, page in enumerate(missing, start=1):
            prefix = temp / f"page-{page:03d}"
            subprocess.run(
                ["pdftoppm", "-f", str(page), "-l", str(page), "-r", "300", "-gray", "-png", "-singlefile", str(PDF), str(prefix)],
                check=True,
            )
            image = prefix.with_suffix(".png")
            started = time.perf_counter()
            results = list(ocr.predict(str(image)))
            if len(results) != 1:
                raise RuntimeError(f"Expected one OCR result for page {page}, got {len(results)}")
            payload = results[0].json
            payload["book_reader_meta"] = {
                "pdf_page": page,
                "seconds": round(time.perf_counter() - started, 2),
                "size": "small",
                "source": "PaddleOCR PP-OCRv6 small",
            }
            (OCR_DIR / f"page-{page:03d}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            image.unlink(missing_ok=True)
            print(json.dumps({"completed": page, "of": len(missing), "position": index}, ensure_ascii=False), flush=True)
    write_text_and_index()


if __name__ == "__main__":
    main()
