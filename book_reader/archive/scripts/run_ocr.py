"""Render and OCR the source PDF one page at a time with resume support."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOK = ROOT / "book_reader"
PDF = ROOT / "走出戈壁-单伟健.pdf"
OCR_DIR = BOOK / "ocr" / "paddle_small"
EXPORT_DIR = BOOK / "output" / "ocr"
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


def write_text_and_index(output: Path = EXPORT_DIR) -> None:
    """Derive disposable text and index files from retained OCR JSON, without a PDF."""
    text_dir = output / "pages"
    text_dir.mkdir(parents=True, exist_ok=True)
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
            (text_dir / f"page-{page:03d}.txt").write_text(
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
    (output / "pages.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", default=f"1-{PAGES}")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--pdf", type=Path, default=Path(os.environ.get("GOBI_SOURCE_PDF", str(PDF))))
    parser.add_argument("--export-only", action="store_true", help="Export retained JSON without the PDF, PaddleOCR, or rendering")
    parser.add_argument("--output", type=Path, default=EXPORT_DIR, help="Directory for disposable pages.json and pages/*.txt")
    parser.add_argument("--cache-dir", type=Path, default=os.environ.get("GOBI_OCR_CACHE_DIR"))
    parser.add_argument("--temp-dir", type=Path, default=os.environ.get("GOBI_TEMP_DIR"))
    parser.add_argument("--det-model-dir", default=os.environ.get("GOBI_OCR_DET_MODEL_DIR"))
    parser.add_argument("--rec-model-dir", default=os.environ.get("GOBI_OCR_REC_MODEL_DIR"))
    args = parser.parse_args()

    if args.export_only:
        write_text_and_index(args.output)
        print(f"Exported OCR text and index to {args.output}")
        return

    OCR_DIR.mkdir(parents=True, exist_ok=True)

    requested = parse_pages(args.pages)
    missing = [
        page
        for page in requested
        if args.force or not (OCR_DIR / f"page-{page:03d}.json").exists()
    ]
    if not missing:
        write_text_and_index(args.output)
        print("All requested pages already exist.")
        return

    if not args.pdf.is_file():
        raise FileNotFoundError(args.pdf)
    # Explicit --cache-dir wins; otherwise honor each existing framework setting.
    if args.cache_dir:
        os.environ["PADDLE_PDX_CACHE_HOME"] = str(args.cache_dir.resolve())
        os.environ["HF_HOME"] = str(args.cache_dir.resolve())
    else:
        cache = Path(tempfile.gettempdir()) / "gobi-paddle-models"
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache))
        os.environ.setdefault("HF_HOME", str(cache))
    if args.temp_dir:
        args.temp_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("OMP_NUM_THREADS", "4")

    from paddleocr import PaddleOCR

    model_dirs = {}
    if args.det_model_dir:
        model_dirs["text_detection_model_dir"] = args.det_model_dir
    if args.rec_model_dir:
        model_dirs["text_recognition_model_dir"] = args.rec_model_dir
    ocr = PaddleOCR(
        **model_dirs,
        text_detection_model_name="PP-OCRv6_small_det",
        text_recognition_model_name="PP-OCRv6_small_rec",
        device="cpu",
        enable_mkldnn=False,
        cpu_threads=4,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    with tempfile.TemporaryDirectory(prefix="gobi-ocr-", dir=args.temp_dir) as temporary:
        temp = Path(temporary)
        for index, page in enumerate(missing, start=1):
            prefix = temp / f"page-{page:03d}"
            subprocess.run(
                ["pdftoppm", "-f", str(page), "-l", str(page), "-r", "300", "-gray", "-png", "-singlefile", str(args.pdf), str(prefix)],
                check=True,
            )
            image = prefix.with_suffix(".png")
            started = time.perf_counter()
            results = list(ocr.predict(str(image)))
            if len(results) != 1:
                raise RuntimeError(f"Expected one OCR result for page {page}, got {len(results)}")
            payload = results[0].json
            payload["res"]["input_path"] = image.name
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
    write_text_and_index(args.output)


if __name__ == "__main__":
    main()
