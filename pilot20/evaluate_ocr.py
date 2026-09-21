"""Compare two manually checked excerpts with both OCR engines."""

import json
import re
import unicodedata
from pathlib import Path

PILOT = Path(__file__).resolve().parent

# Checked against the page images, including names, numerals and punctuation.
GOLD = {
    15: (
        "1950年9月15日，由麥克亞瑟（Douglas MacArthur）將軍指揮的聯合國軍，"
        "在韓國西海岸距漢城約40公里的仁川港登陸。260多艘海軍艦艇，"
        "包括6艘航空母艦以及7.5萬名士兵參與了行動，這是自第二次世界大戰"
        "中聯軍在法國諾曼第登陸以來最大規模的軍事部署。此時，北朝鮮人民軍"
        "已將聯合國軍逼至朝鮮半島東南角釜山的一隅，差點就要將他們趕入太平洋。"
        "對北朝鮮人民軍來說，可謂勝利在即。然而，麥克亞瑟將軍的部隊在"
        "仁川成功登陸，包抄了北朝鮮軍隊的後路，徹底扭轉了戰局。其後，"
        "聯合國軍大舉反攻，勢如破竹，10月越過分隔南北朝鮮的三八線，"
        "月底逼近中朝邊境線——鴨綠江。麥克亞瑟揚言，戰爭將在聖誕節結束。"
    ),
    19: (
        "1945年3月10日，羅斯福（Franklin D. Roosevelt）總統給中國共產黨的"
        "領袖毛澤東寫了一封信。「親愛的毛先生」，羅斯福寫道，「我從雅爾達"
        "會議一回來，就收到了你1944年11月10日的信。非常高興獲悉你本人對"
        "中國事態發展的看法。」羅斯福提及毛澤東在來信中強調了中國人民的團結，"
        "羅斯福希望毛澤東和國民黨領袖蔣介石能夠攜手合作打敗日本。羅斯福最後說，"
        "「正如你所說，中國人民和美國人民之間的友誼有着悠久的傳統而且根深蒂固，"
        "我相信，中國人民和美國人民的合作將極其有助於我們取得勝利及持久的和平。」"
    ),
}
ENDS = {15: "聖誕節結束。", 19: "持久的和平。"}


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


results = []
for page, gold in GOLD.items():
    for engine in ("paddle_small", "tesseract"):
        if engine == "paddle_small":
            payload = json.loads((PILOT / "ocr" / engine / f"page-{page:03d}.json").read_text(encoding="utf-8"))
            ocr_text = "".join(payload["res"]["rec_texts"])
        else:
            ocr_text = (PILOT / "ocr" / engine / f"page-{page:03d}.txt").read_text(encoding="utf-8")
        ocr_text = normalize(ocr_text)
        start = ocr_text.index(str(1950 if page == 15 else 1945))
        end_marker = normalize(ENDS[page])
        end = ocr_text.index(end_marker, start) + len(end_marker)
        candidate = ocr_text[start:end]
        reference = normalize(gold)
        errors = distance(reference, candidate)
        results.append({
            "page": page,
            "engine": engine,
            "reference_characters": len(reference),
            "edit_errors": errors,
            "cer": round(errors / len(reference), 4),
            "candidate": candidate,
        })

(PILOT / "ocr" / "quality_sample.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
for result in results:
    print(result["page"], result["engine"], result["reference_characters"], result["edit_errors"], result["cer"])
