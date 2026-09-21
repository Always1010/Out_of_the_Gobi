"""Run the selected PaddleOCR pipeline over rendered pilot pages."""

import argparse
import json
import os
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilot20"
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(ROOT / "models" / "paddleocr"))
os.environ.setdefault("OMP_NUM_THREADS", "4")

import psutil  # noqa: E402
from paddleocr import PaddleOCR  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pages", nargs="+", type=int)
    parser.add_argument("--size", choices=("small", "medium"), default="small")
    args = parser.parse_args()

    ocr = PaddleOCR(
        text_detection_model_name=f"PP-OCRv6_{args.size}_det",
        text_recognition_model_name=f"PP-OCRv6_{args.size}_rec",
        device="cpu",
        enable_mkldnn=False,
        cpu_threads=4,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    out_dir = PILOT / "ocr" / f"paddle_{args.size}"
    out_dir.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    for page in args.pages:
        image = PILOT / "tmp" / f"page-{page:03d}.png"
        peak_rss = [process.memory_info().rss]
        stop = threading.Event()

        def sample_memory() -> None:
            while not stop.wait(0.1):
                peak_rss[0] = max(peak_rss[0], process.memory_info().rss)

        monitor = threading.Thread(target=sample_memory, daemon=True)
        monitor.start()
        t0 = time.perf_counter()
        try:
            results = list(ocr.predict(str(image)))
        finally:
            stop.set()
            monitor.join()
        seconds = round(time.perf_counter() - t0, 2)
        if len(results) != 1:
            raise RuntimeError(f"Expected one result for {image}, got {len(results)}")
        payload = results[0].json
        payload["pilot_meta"] = {
            "pdf_page": page,
            "seconds": seconds,
            "peak_process_rss_mb": round(peak_rss[0] / 2**20, 1),
            "size": args.size,
        }
        output = out_dir / f"page-{page:03d}.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload["pilot_meta"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
