"""Run the Traditional Chinese Tesseract comparison on selected pages."""

import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilot20"
EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSDATA = ROOT / "models" / "tesseract"
PAGES = (6, 8, 10, 15, 19, 20)


def main() -> None:
    out_dir = PILOT / "ocr" / "tesseract"
    out_dir.mkdir(parents=True, exist_ok=True)
    for page in PAGES:
        image = PILOT / "tmp" / f"page-{page:03d}.png"
        cmd = [
            str(EXE), str(image), "stdout", "--tessdata-dir", str(TESSDATA),
            "-l", "chi_tra+eng", "--psm", "3",
        ]
        start = time.perf_counter()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        monitor = psutil.Process(proc.pid)
        peak_rss = 0
        while proc.poll() is None:
            try:
                peak_rss = max(peak_rss, monitor.memory_info().rss)
            except psutil.Error:
                break
            time.sleep(0.1)
        stdout, stderr = proc.communicate()
        if proc.returncode:
            raise RuntimeError(stderr.decode("utf-8", errors="replace"))
        text = stdout.decode("utf-8", errors="replace")
        (out_dir / f"page-{page:03d}.txt").write_text(text, encoding="utf-8")
        meta = {
            "pdf_page": page,
            "seconds": round(time.perf_counter() - start, 2),
            "peak_process_rss_mb": round(peak_rss / 2**20, 1),
        }
        (out_dir / f"page-{page:03d}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(meta, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
