"""Create human-readable page text and a compact OCR index."""

import json
import statistics
from pathlib import Path

PILOT = Path(__file__).resolve().parent
SOURCE = PILOT / "ocr" / "paddle_small"
TEXT = PILOT / "ocr" / "text"
TEXT.mkdir(parents=True, exist_ok=True)

index = []
for page in range(1, 21):
    payload = json.loads((SOURCE / f"page-{page:03d}.json").read_text(encoding="utf-8"))
    result = payload["res"]
    lines = result["rec_texts"]
    content = "\n".join(lines).strip() + "\n"
    (TEXT / f"page-{page:03d}.txt").write_text(content, encoding="utf-8")
    scores = result["rec_scores"]
    index.append({
        "pdf_page": page,
        "line_count": len(lines),
        "character_count": len("".join(lines)),
        "mean_line_confidence": round(statistics.mean(scores), 3) if scores else None,
        **payload["pilot_meta"],
    })

(PILOT / "ocr" / "index.json").write_text(
    json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Wrote {len(index)} page text files and index.json")
