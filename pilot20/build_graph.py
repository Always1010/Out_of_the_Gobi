"""Curated, page-grounded knowledge graph for the first 20 PDF pages."""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
nodes = []
edges = []
ids = set()


def node(id, label, kind, detail=""):
    assert id not in ids, id
    ids.add(id)
    nodes.append(dict(id=id, label=label, kind=kind, detail=detail))


def edge(source, target, label, page, quote, section="正文", external=None):
    assert source in ids and target in ids, (source, target)
    book_text = (BASE / "ocr" / "text" / f"page-{page:03d}.txt").read_text(encoding="utf-8")
    compact = lambda s: re.sub(r"\s+", "", s)
    assert compact(quote) in compact(book_text), (page, quote)
    edges.append(dict(source=source, target=target, label=label,
                      evidence=dict(pdf_page=page, quote=quote, section=section,
                                    external=external)))


for id, label, detail in [
    ("shan", "單偉建", "本書作者；試點中心人物"),
    ("yellen", "珍妮特·耶倫", "前言作者、博士導師"),
    ("macarthur", "麥克亞瑟", "1950 年仁川登陸指揮者"),
    ("fdr", "羅斯福", "1945 年致毛澤東信函的寫信人"),
    ("mao", "毛澤東", "1945 年信函收信人；新中國領導人"),
    ("chiang", "蔣介石", "書中描述的國民黨領袖"),
    ("truman", "杜魯門", "1950 年美國總統"),
    ("zhou", "周恩來", "1945 年擬與毛澤東訪美；1927 年南昌起義人物"),
    ("hurley", "赫爾利", "書中稱其未轉達訪美提議"),
    ("shi", "石濱", "單偉建的妻子"),
    ("bo", "單博", "單偉建的兒子"),
    ("lian", "單蓮蓮", "單偉建的女兒"),
    ("liu", "劉小彤", "內蒙戈壁時期的戰友、照片拍攝者"),
    ("chen", "陳雪", "中文版文稿修改者"),
    ("zhou_liqin", "周麗琴", "中文版出版經理"),
    ("guo", "郭曉敏", "中文版形成過程中提供幫助"),
]:
    node(id, label, "人物", detail)

for id, label in [
    ("shandong", "山東省"), ("gobi", "內蒙古戈壁"),
    ("beijing", "北京"), ("berkeley", "加州大學柏克萊分校"),
    ("hongkong", "香港"), ("incheon", "仁川港"),
    ("taiwan", "台灣海峽"), ("nanchang", "南昌"),
    ("washington", "華盛頓"), ("korea", "朝鮮半島"),
]:
    node(id, label, "地點")

for id, label in [
    ("t1950_09_15", "1950-09-15"), ("t1953_10", "1953-10"),
    ("t1966", "1966 年"), ("t1982_09", "1982-09"),
    ("t1987", "1987 年"), ("t1993", "1993 年"),
    ("t1998", "1998 年"), ("t2010", "2010 年"),
    ("t2018_10", "2018-10"), ("t2019_01", "2019-01"),
    ("t2020_03_26", "2020-03-26"), ("t1945_03_10", "1945-03-10"),
    ("t1949_10_01", "1949-10-01"), ("t1950_01_05", "1950-01-05"),
    ("t1950_06_25", "1950-06-25"), ("t1958", "1958 年"),
    ("t1927_08_01", "1927-08-01"),
]:
    node(id, label, "时间")


def event(id, label, date, summary, page, quote, people=(), places=(),
          time=None, section="正文", external=None, topic="人生"):
    node(id, label, "事件", summary)
    if topic == "人生":
        edge("shan", id, "主題人物", page, quote, section, external)
    for p in people:
        edge(p, id, "參與／相關", page, quote, section, external)
    for place in places:
        edge(id, place, "發生地／關聯地", page, quote, section, external)
    if time:
        edge(id, time, "發生於", page, quote, section, external)
    # Separate timeline metadata avoids treating undated relative ages as precise dates.
    nodes[-1]["date"] = date
    nodes[-1]["topic"] = topic
    nodes[-1]["page"] = page


event("e_birth", "單偉建出生", "1953-10", "作者自述 1953 年 10 月出生於山東省。",
      15, "1953年10月我出生在山東省", places=["shandong"], time="t1953_10")
event("e_school", "文革中斷學業", "1966", "作者簡介稱小學六年級時文革爆發，正規教育中斷。",
      4, "單偉建小學六年級時爆發文化大革命，正規教育被迫中斷", time="t1966", section="作者簡介")
event("e_gobi", "被分配至內蒙生產建設兵團", "1969?", "作者簡介稱失學三年後被分配；年份由 1966 推算，故標問號。",
      4, "三年後更被分配到內蒙生產建設兵團", places=["gobi"], section="作者簡介")
event("e_beitai", "進入北京對外貿易學院", "1970年代中後期?", "作者簡介記載失學近十年後入學，未給確切年份。",
      4, "進入北京對外貿易學院", places=["beijing"], section="作者簡介")
event("e_berkeley", "在柏克萊攻讀博士", "1982-09", "耶倫前言記述 1982 年 9 月首次與作者見面並任其學術指導教授。",
      8, "1982年9月，一個陽光明媚的日子，單偉建第一次出現在我的辦公室", people=["yellen"], places=["berkeley"], time="t1982_09", section="耶倫前言")
event("e_grad", "取得博士學位", "1987", "耶倫前言提及 1987 年作者畢業聚會。",
      9, "1987年單偉建慶祝畢業的聚會", time="t1987", section="耶倫前言")
event("e_wharton", "任教沃頓商學院", "1987後", "作者簡介記載取得博士學位後任教六年。",
      4, "繼而任教賓夕法尼亞大學沃頓商學院", section="作者簡介")
event("e_jpm", "加入摩根大通並遷居香港", "1993", "作者簡介明記年份及遷居地。",
      4, "單偉建在1993年加入摩根大通銀行，舉家從美國遷居香港", places=["hongkong"], time="t1993", section="作者簡介")
event("e_newbridge", "加入新橋投資", "1998", "作者簡介記載加入新橋投資並任執行合伙人。",
      4, "1998年加入美國新橋投資公司", time="t1998", section="作者簡介")
event("e_pag", "共同創辦太盟投資集團", "2010", "作者簡介記載其為創辦人之一、董事長兼首席執行官。",
      4, "2010年單偉建成為太盟投資集團", time="t2010", section="作者簡介")
event("e_english", "英文版出版", "2019-01", "自序記載英文版在美國出版。",
      10, "2019年1月，英文版的《走出戈壁我的中美故事》在美國出版", time="t2019_01", section="自序")
event("e_foreword", "耶倫完成前言", "2018-10", "前言落款日期。",
      9, "2018年10月", people=["yellen"], time="t2018_10", section="耶倫前言")
event("e_chinese_preface", "中文版自序落款", "2020-03-26", "自序在香港落款；中文版为改写，非逐章翻译。",
      13, "2020年3月26日於香港", places=["hongkong"], time="t2020_03_26", section="自序")

event("e_incheon", "仁川登陸", "1950-09-15", "作者以仁川登陸开篇。美國國家檔案館資料獨立印證日期、地點及麥克亞瑟指揮。",
      15, "1950年9月15日，由麥克亞瑟（Douglas MacArthur）將軍指揮的聯合國軍", people=["macarthur"], places=["incheon", "korea"], time="t1950_09_15", topic="歷史背景",
      external="https://www.archives.gov/calendar/event/korea-75-macarthur-s-gamble-the-inchon-landing")
event("e_fdr_letter", "羅斯福致毛澤東信", "1945-03-10", "第一章記述信函及希望毛、蔣合作抗日；此處只標為書中敘述。",
      19, "1945年3月10日，羅斯福（Franklin D.Roosevelt）總統給中國共產黨的領袖毛澤東寫了一封信", people=["fdr", "mao", "chiang"], time="t1945_03_10", topic="歷史背景")
event("e_washington", "毛、周擬訪華盛頓", "1945", "第一章稱提議遭赫爾利拒絕且未轉達；尚未獨立核實。",
      19, "毛澤東曾提出要和周恩來一起去華盛頓拜訪羅斯福", people=["mao", "zhou", "hurley", "fdr"], places=["washington"], topic="歷史背景")
event("e_prc", "中華人民共和國成立", "1949-10-01", "作者於開場白和第一章都提及此事。",
      17, "1949年10月1日，毛澤東宣布中華人民共和國成立", people=["mao"], time="t1949_10_01", topic="歷史背景")
event("e_truman", "杜魯門發表台灣政策聲明", "1950-01-05", "第一章称美国当时表示若共產黨軍隊攻台，美國將不干預。",
      19, "1950年1月5日，美國總統杜魯門宣布", people=["truman"], places=["taiwan"], time="t1950_01_05", topic="歷史背景")
event("e_korean_war", "韓戰爆發", "1950-06-25", "第一章记述北朝鮮軍隊越過三八線。",
      20, "6月25日，北朝鮮的軍隊越過三八線", places=["korea"], time="t1950_06_25", topic="歷史背景")
event("e_seventh_fleet", "美第七艦隊進入台灣海峽", "1950-06-27", "書稱韓戰爆發兩天後杜魯門下令；具體日由 6 月 25 日推算。",
      20, "兩天後，杜魯門下令美國第七艦隊進入台灣海峽", people=["truman"], places=["taiwan"], topic="歷史背景")
event("e_leap", "大躍進運動", "1958", "第一章記述毛澤東發起全國性的政治經濟運動。",
      20, "1958年，他發起了「大躍進」運動", people=["mao"], time="t1958", topic="歷史背景")
event("e_nanchang", "南昌起義", "1927-08-01", "開場白記述周恩來等人在南昌發動武裝起義。",
      17, "1927年8月1日，以周恩來為首的共產黨人在南昌發動武裝起義", people=["zhou"], places=["nanchang"], time="t1927_08_01", topic="歷史背景")

edge("yellen", "shan", "博士導師", 8, "我是他的學術指導教授", "耶倫前言")
edge("shi", "shan", "妻子", 13, "妻子石濱", "自序")
edge("bo", "shan", "兒子", 13, "兒子單博", "自序")
edge("lian", "shan", "女兒", 13, "女兒單蓮蓮", "自序")
edge("liu", "shan", "戈壁戰友", 12, "劉小彤是我在內蒙戈壁時患難與共的戰友", "自序")
edge("liu", "e_gobi", "拍攝戈壁照片", 12, "本書中所有在戈壁灘上的照片，都是他當年拍攝和沖曬的", "自序")
edge("chen", "shan", "修改中文版文稿", 12, "我請她修改我的中文稿，她爽快地答應了", "自序")
edge("zhou_liqin", "e_chinese_preface", "協助中文版出版", 10, "在資深出版經理周麗琴女士和她的同事、編輯孜孜不倦的努力之下", "自序")
edge("guo", "e_chinese_preface", "協助中文版文稿", 10, "我的秘書郭曉敏女士給予了很多幫助", "自序")
graph = {
    "title": "《走出戈壁》前 20 页人物—事件—时间—地点知识图谱",
    "scope": "PDF 物理页 1–20；正文至第一章第 20 页中途。页码均指 PDF 物理页。",
    "nodes": nodes,
    "edges": edges,
    "external_sources": [{"title": "U.S. National Archives: MacArthur's Gamble: The Inchon Landing",
                          "url": "https://www.archives.gov/calendar/event/korea-75-macarthur-s-gamble-the-inchon-landing",
                          "applies_to": "仁川登陸日期、地點、指揮官"}],
}
out = BASE / "data" / "graph.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(nodes)} nodes, {len(edges)} edges -> {out}")
