"""Build the portable, offline Simplified Chinese reader."""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from opencc import OpenCC

from assemble_transcript import to_mainland_simplified


ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "text"
DIST = ROOT / "site" / "dist"
IMAGE_SOURCE = ROOT / "images" / "pages"


def plain_text(markdown: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", markdown, flags=re.S)
    text = re.sub(r"^# .*?$", "", text, flags=re.M)
    return re.sub(r"\s+", " ", text).strip()


def content_html(markdown: str, title: str, captions: dict[str, list[str]]) -> str:
    chunks: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        nonlocal paragraph
        value = "".join(part.strip() for part in paragraph).strip()
        paragraph = []
        # The scanned chapter-opening page usually repeats the title after its H1.
        if not value or value == title or re.fullmatch(r"第[一二三四五六七八九十百]+章", value):
            return
        if value == "★★★":
            chunks.append(f'<div class="scene-break" data-block="{len(chunks)}" aria-label="段落分隔">★★★</div>')
        else:
            chunks.append(f'<p data-block="{len(chunks)}">{html.escape(value)}</p>')

    for raw in markdown.splitlines():
        line = raw.strip()
        image = re.fullmatch(r"<!-- Image plate: .*?page-(\d{3})\.jpg -->", line)
        if image:
            flush()
            pdf_page = int(image.group(1))
            image_name = f"page-{image.group(1)}.jpg"
            page_captions = captions.get(str(pdf_page), [])
            caption_text = f"原书图片 · PDF 第 {pdf_page} 页"
            if page_captions:
                caption_text += " · " + "；".join(page_captions)
            caption_html = "".join(
                f'<span class="plate-caption">{html.escape(value)}</span>'
                for value in page_captions
            )
            chunks.append(
                f'<figure class="plate" data-block="{len(chunks)}">'
                f'<button class="plate-button" type="button" data-image="images/{image_name}" '
                f'data-caption="{html.escape(caption_text, quote=True)}">'
                f'<img src="images/{image_name}" alt="原书图片，PDF 第 {pdf_page} 页" loading="lazy"></button>'
                f'<figcaption><span class="plate-source">原书图片 · PDF 第 {pdf_page} 页 · 点击放大</span>'
                f'{caption_html}</figcaption></figure>'
            )
        elif not line or line == "---":
            flush()
        elif line.startswith("# "):
            flush()
        else:
            paragraph.append(raw)
    flush()
    return "\n".join(chunks)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def main() -> None:
    chapters = json.loads((TEXT / "chapters.json").read_text(encoding="utf-8"))
    image_entries = json.loads((ROOT / "images" / "images.json").read_text(encoding="utf-8"))["pages"]
    image_pages = {str(entry["pdf_page"]) for entry in image_entries}
    raw_captions = json.loads((ROOT / "images" / "captions.json").read_text(encoding="utf-8"))["pages"]
    if not set(raw_captions) <= image_pages:
        raise ValueError("A caption points to a page that is not in the image manifest")
    converter = OpenCC("tw2sp")
    captions = {
        page: [to_mainland_simplified(value, converter) for value in values]
        for page, values in raw_captions.items()
    }
    entries = []
    for index, chapter in enumerate(chapters, start=1):
        source = TEXT / "simplified-continuous" / f"{index:02d}-{chapter['id']}.md"
        markdown = source.read_text(encoding="utf-8")
        image_pages = re.findall(r"<!-- Image plate: .*?page-(\d{3})\.jpg -->", markdown)
        caption_search = " ".join(value for page in image_pages for value in captions.get(str(int(page)), []))
        entries.append({
            "id": f"section-{index:02d}",
            "number": index,
            "title": chapter["title_simplified"],
            "label": f"第 {chapter['number']} 章" if "number" in chapter else ("后记" if chapter["id"] == "afterword" else "卷首"),
            "pdfPage": chapter["pdf_page_start"],
            "html": content_html(markdown, chapter["title_simplified"], captions),
            "searchText": f"{plain_text(markdown)} {caption_search}".strip(),
        })

    DIST.mkdir(parents=True, exist_ok=True)
    target_images = DIST / "images"
    if target_images.exists():
        shutil.rmtree(target_images)
    target_images.mkdir()
    for entry in image_entries:
        source = IMAGE_SOURCE / Path(entry["asset"]).name
        shutil.copy2(source, target_images / source.name)
    payload = json.dumps({"title": "走出戈壁", "chapters": entries}, ensure_ascii=False).replace("</", "<\\/")
    write_text(DIST / "data.js", f"window.BOOK = {payload};\n")
    write_text(DIST / "styles.css", STYLES)
    write_text(DIST / "app.js", APP)
    write_text(DIST / "index.html", INDEX)
    print(f"Built {len(entries)} chapters and {len(image_entries)} image pages in {DIST}")


INDEX = '''<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>走出戈壁 · 离线阅读</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="topbar">
    <div class="book-controls">
      <button id="toc-toggle" class="toc-toggle" type="button" aria-controls="toc-panel" aria-expanded="true">收起目录</button>
      <a class="brand" href="#section-01">走出戈壁 <span>单伟建</span></a>
    </div>
    <div class="tools">
      <select id="reading-mode" aria-label="阅读方式" title="选择滚动或翻页阅读"><option value="scroll">滚动阅读</option><option value="pages">翻页阅读</option></select>
      <label class="search"><span class="visually-hidden">搜索全书</span><input id="search" type="search" placeholder="搜索全书" autocomplete="off"></label>
      <button id="font-down" type="button" title="缩小字体">A−</button>
      <button id="font-up" type="button" title="放大字体">A＋</button>
      <button id="theme" type="button" title="切换明暗主题">◐</button>
    </div>
  </header>
  <div id="search-results" class="search-results" hidden></div>
  <div class="layout">
    <aside id="toc-panel" class="toc-panel"><div class="toc-head">目录 <span id="chapter-count"></span></div><nav id="toc" aria-label="章节目录"></nav></aside>
    <main id="reader" tabindex="-1">
      <div class="reader-meta"><span id="location">载入中</span><a id="source-link" target="_blank" rel="noopener">查看原始 PDF 页</a></div>
      <article id="chapter"></article>
      <nav class="chapter-nav" aria-label="章节导航"><button id="prev" type="button">← 上一节</button><button id="next" type="button">下一节 →</button></nav>
      <nav class="page-nav" aria-label="翻页导航">
        <button id="page-prev-chapter" type="button" aria-label="上一章" title="上一章：↑">« <span class="nav-label">上一章</span></button>
        <button id="page-prev" type="button" aria-label="上一页" title="上一页：←">‹ <span class="nav-label">上一页</span></button>
        <span class="page-status"><span id="page-count" aria-live="polite">1 / 1</span><small class="key-hint">← → 翻页 · ↑ ↓ 换章</small></span>
        <button id="page-next" type="button" aria-label="下一页" title="下一页：→"><span class="nav-label">下一页</span> ›</button>
        <button id="page-next-chapter" type="button" aria-label="下一章" title="下一章：↓"><span class="nav-label">下一章</span> »</button>
      </nav>
    </main>
  </div>
  <dialog id="image-dialog"><button id="close-image" type="button" aria-label="关闭图片">×</button><img id="dialog-image" alt=""><p id="dialog-caption"></p></dialog>
  <script src="data.js"></script><script src="app.js"></script>
</body></html>'''


STYLES = '''
:root { --ink:#20251f; --muted:#6c7068; --paper:#fbfaf5; --edge:#e3e1d6; --pine:#1f4b42; --header-bg:#1f4b42; --accent:#b26b36; --body-size:19px; }
* { box-sizing:border-box; } body { margin:0; color:var(--ink); background:var(--paper); font-family:"Noto Serif CJK SC","Songti SC","STSong","SimSun",serif; }
.topbar { height:64px; display:flex; align-items:center; justify-content:space-between; gap:20px; padding:0 32px; color:#fff; background:var(--header-bg); position:sticky; top:0; z-index:5; box-shadow:0 2px 12px #0002; }
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.book-controls { display:flex; align-items:center; gap:18px; min-width:0; }.toc-toggle { flex:none; border:1px solid #ffffff80; background:transparent; color:#fff; border-radius:5px; padding:6px 10px; font:14px/1.3 inherit; cursor:pointer; white-space:nowrap; }.toc-toggle:hover,.toc-toggle:focus-visible { background:#ffffff24; }
.brand { color:inherit; text-decoration:none; font-size:21px; letter-spacing:.12em; white-space:nowrap; }.brand span { font-size:13px; letter-spacing:.05em; opacity:.7; margin-left:8px; }
.tools { display:flex; align-items:center; gap:7px; }.tools button { border:1px solid #ffffff55; background:transparent; color:white; border-radius:5px; height:31px; cursor:pointer; } #reading-mode { height:31px; border:1px solid #ffffff80; border-radius:5px; background:var(--header-bg); color:#fff; padding:3px 6px; font:14px inherit; cursor:pointer; } #reading-mode option { background:#fff; color:#20251f; }.search input { width:180px; height:31px; padding:4px 10px; border:0; border-radius:5px; font:14px inherit; }
.layout { max-width:1360px; margin:auto; display:grid; grid-template-columns:265px minmax(0, 1fr); }.toc-panel { border-right:1px solid var(--edge); min-height:calc(100vh - 64px); padding:34px 23px; position:sticky; top:64px; height:calc(100vh - 64px); overflow:auto; }.toc-head { color:var(--pine); font-weight:bold; letter-spacing:.13em; padding-bottom:13px; border-bottom:1px solid var(--edge); }.toc-head span { float:right; color:var(--muted); font-size:12px; letter-spacing:0; }
body.toc-collapsed .layout { grid-template-columns:minmax(0,1fr); } body.toc-collapsed .toc-panel { display:none; }
#toc { padding-top:12px; } .toc-item { width:100%; display:block; padding:8px 7px; text-align:left; border:0; background:none; color:var(--ink); font:15px/1.35 inherit; cursor:pointer; border-radius:4px; }.toc-item:hover,.toc-item.active { background:#e9efe9; color:var(--pine); }.toc-item .toc-num { display:inline-block; width:31px; color:var(--muted); font-size:12px; }
#reader { max-width:820px; width:100%; margin:0 auto; padding:41px 54px 88px; }.reader-meta { display:flex; justify-content:space-between; gap:12px; color:var(--muted); font-size:13px; margin-bottom:25px; }.reader-meta a { color:var(--pine); text-decoration:none; }.reader-meta a:hover { text-decoration:underline; }
#chapter h1 { margin:0 0 8px; color:var(--pine); font-size:34px; letter-spacing:.08em; font-weight:600; } .chapter-kicker { color:var(--accent); font-size:14px; letter-spacing:.15em; margin-bottom:18px; } #chapter p { margin:0 0 1em; font-size:var(--body-size); line-height:2.05; text-align:justify; text-indent:2em; letter-spacing:.025em; } .scene-break { color:var(--accent); text-align:center; letter-spacing:.45em; margin:2em 0; font-size:15px; }
.chapter-heading { break-inside:avoid; }
.plate { margin:2.6em auto; text-align:center; }.plate-button { max-width:100%; padding:0; border:0; background:transparent; cursor:zoom-in; }.plate img { display:block; max-width:100%; max-height:760px; margin:auto; box-shadow:0 7px 26px #0003; }.plate figcaption { max-width:700px; margin:10px auto 0; font-size:13px; color:var(--muted); line-height:1.7; }.plate-source { display:block; text-align:center; }.plate-caption { display:block; margin-top:7px; text-align:left; }.chapter-nav { display:flex; justify-content:space-between; gap:16px; border-top:1px solid var(--edge); padding-top:27px; margin-top:56px; }.chapter-nav button { padding:9px 14px; border:1px solid var(--edge); color:var(--pine); background:transparent; border-radius:4px; font:15px inherit; cursor:pointer; }.chapter-nav button:hover:not(:disabled) { background:#edf2ed; }.chapter-nav button:disabled { opacity:.35; cursor:default; }
.page-nav { display:none; align-items:center; justify-content:space-between; gap:5px; border-top:1px solid var(--edge); padding-top:10px; margin-top:10px; }.page-nav button { padding:7px 9px; border:1px solid var(--edge); color:var(--pine); background:transparent; border-radius:4px; font:14px inherit; cursor:pointer; white-space:nowrap; }.page-nav button:disabled { opacity:.35; cursor:default; }.page-status { min-width:100px; text-align:center; color:var(--muted); white-space:nowrap; } #page-count { display:block; font:14px/1.4 sans-serif; }.key-hint { display:block; font:12px/1.3 sans-serif; }
body.page-mode { height:100dvh; overflow:hidden; } body.page-mode .layout { height:calc(100dvh - var(--header-height,64px)); } body.page-mode .toc-panel { height:calc(100dvh - var(--header-height,64px)); min-height:0; top:var(--header-height,64px); } body.page-mode #reader { display:flex; flex-direction:column; height:100%; padding-top:18px; padding-bottom:14px; } body.page-mode .reader-meta { flex:none; margin-bottom:13px; } body.page-mode #chapter { flex:1; width:100%; min-width:0; min-height:0; column-fill:auto; column-gap:28px; overflow:hidden; overscroll-behavior:contain; } body.page-mode #chapter p { orphans:2; widows:2; } body.page-mode .plate { break-inside:avoid; margin:1.2em auto; } body.page-mode .chapter-nav { display:none; } body.page-mode .page-nav { display:flex; }
.search-results { position:fixed; z-index:10; top:57px; right:96px; width:min(490px,calc(100vw - 30px)); max-height:55vh; overflow:auto; padding:8px; border:1px solid var(--edge); border-radius:0 0 8px 8px; background:var(--paper); box-shadow:0 10px 26px #0003; }.result { width:100%; display:block; text-align:left; padding:11px; border:0; background:transparent; border-bottom:1px solid var(--edge); font:14px/1.55 inherit; cursor:pointer; }.result strong { color:var(--pine); display:block; margin-bottom:3px; }.result:hover { background:#edf2ed; }.visually-hidden { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); }
dialog { width:min(1000px,94vw); max-height:94vh; padding:18px; border:0; background:var(--paper); color:var(--ink); box-shadow:0 15px 50px #0008; } dialog::backdrop { background:#000b; } dialog img { display:block; max-width:100%; max-height:80vh; margin:auto; } dialog p { text-align:center; color:var(--muted); } #close-image { float:right; border:0; background:transparent; font-size:29px; cursor:pointer; color:var(--ink); }
body.dark { --ink:#e5e4dc; --muted:#a7aaa1; --paper:#1c211e; --edge:#3e4740; --pine:#9bc4b6; --header-bg:#254f45; --accent:#d9a06d; } body.dark .toc-item:hover,body.dark .toc-item.active,body.dark .chapter-nav button:hover:not(:disabled),body.dark .result:hover { background:#2c3830; } body.dark .search input { background:#eff0eb; color:#20251f; }
@media (max-width:850px) { .topbar { height:auto; min-height:58px; padding:10px 15px; }.tools { flex-wrap:wrap; justify-content:flex-end; }.search input { width:132px; }.layout { display:block; }.toc-panel { position:fixed; top:var(--header-height,58px); left:0; right:0; height:auto; max-height:min(70vh,620px); min-height:0; overflow:auto; z-index:4; border-right:0; border-bottom:1px solid var(--edge); padding:16px 20px; background:var(--paper); box-shadow:0 10px 25px #0002; }.toc-head { display:block; } #toc { padding-top:8px; }.toc-item { width:100%; padding:9px 7px; }.toc-num { width:31px; }.toc-item .toc-label { display:inline; } #reader { padding:30px 20px 68px; }.reader-meta { margin-bottom:21px; }.reader-meta a { white-space:nowrap; } #chapter h1 { font-size:28px; } #chapter p { font-size:var(--body-size); line-height:1.92; }.search-results { top:var(--header-height,58px); right:15px; } }
@media (max-width:850px) { body.page-mode .toc-panel { height:auto; max-height:min(70vh,620px); } body.page-mode #reader { padding:14px 20px 11px; } body.page-mode .reader-meta { margin-bottom:9px; } }
@media (max-width:540px) { .topbar { display:grid; grid-template-columns:minmax(0,1fr); gap:8px; }.book-controls { justify-content:space-between; }.brand { font-size:18px; }.brand span { display:none; }.tools { width:100%; } #reading-mode { max-width:100px; }.search { flex:1; min-width:55px; }.search input { width:100%; }.page-nav .nav-label,.key-hint { display:none; }.page-status { min-width:70px; }.page-nav button { min-width:32px; font-size:20px; padding:3px 5px; } }
'''


APP = '''
(() => {
  const book = window.BOOK;
  const bookOpening = '<section class="book-opening"><figure class="plate" data-block="-3"><button class="plate-button" type="button" data-image="images/page-001.jpg" data-caption="原书封面 · PDF 第 1 页"><img src="images/page-001.jpg" alt="《走出戈壁》原书封面" loading="eager"></button><figcaption>原书封面 · 点击放大</figcaption></figure><figure class="plate" data-block="-2"><button class="plate-button" type="button" data-image="images/page-002.jpg" data-caption="原书题字页 · PDF 第 2 页"><img src="images/page-002.jpg" alt="原书题字页" loading="lazy"></button><figcaption>原书题字页 · 点击放大</figcaption></figure></section>';
  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[char]);
  const toc = $('#toc'), chapterEl = $('#chapter'), reader = $('#reader');
  const settingsKey = 'gobi-reader-settings', positionKey = 'gobi-reader-position';
  let settings = { size: 19, dark: false, tocOpen: window.matchMedia('(min-width:851px)').matches, mode: 'scroll' };
  try { settings = { ...settings, ...JSON.parse(localStorage.getItem(settingsKey)) }; } catch (_) {}
  if (!['scroll', 'pages'].includes(settings.mode)) settings.mode = 'scroll';
  let currentSection = book.chapters[0], pageIndex = 0, pageCount = 1, pageStep = 0;
  let pendingTarget = null, layoutFrame = 0, layoutTarget = null, lastBlock = null, keepLastPage = false;
  function saveSettings() { localStorage.setItem(settingsKey, JSON.stringify(settings)); }
  function applySettings() {
    document.documentElement.style.setProperty('--body-size', settings.size + 'px');
    document.body.classList.toggle('dark', settings.dark);
    document.body.classList.toggle('toc-collapsed', !settings.tocOpen);
    document.body.classList.toggle('page-mode', settings.mode === 'pages');
    $('#toc-toggle').setAttribute('aria-expanded', String(settings.tocOpen));
    $('#toc-toggle').textContent = settings.tocOpen ? '收起目录' : '展开目录';
    $('#reading-mode').value = settings.mode;
  }
  function updateHeaderHeight() { document.documentElement.style.setProperty('--header-height', $('.topbar').offsetHeight + 'px'); }
  applySettings();
  updateHeaderHeight();
  window.addEventListener('resize', () => {
    updateHeaderHeight();
    if (settings.mode === 'pages') scheduleLayout({ block: lastBlock });
  });
  $('#chapter-count').textContent = book.chapters.length + ' 节';
  toc.innerHTML = book.chapters.map(c => `<button class="toc-item" data-id="${c.id}"><span class="toc-num">${String(c.number).padStart(2,'0')}</span><span class="toc-label">${c.title}</span></button>`).join('');
  function getChapter(id) { return book.chapters.find(c => c.id === id) || book.chapters[0]; }
  function blocks() { return [...chapterEl.querySelectorAll('[data-block]')]; }
  function visibleBlock() {
    const view = chapterEl.getBoundingClientRect();
    const top = $('.topbar').offsetHeight + 18;
    for (const block of blocks()) {
      for (const rect of block.getClientRects()) {
        if (settings.mode === 'pages') {
          if (rect.right > view.left + 2 && rect.left < view.right - 2 && rect.bottom > view.top + 2 && rect.top < view.bottom - 2) return block.dataset.block;
        } else if (rect.bottom > top && rect.top < window.innerHeight) return block.dataset.block;
      }
    }
    return null;
  }
  function findBlock(id) { return blocks().find(el => el.dataset.block === String(id)); }
  function savePosition() {
    const block = visibleBlock() ?? lastBlock;
    if (block !== null) lastBlock = block;
    localStorage.setItem(positionKey, JSON.stringify({ id: currentSection.id, mode: settings.mode, y: window.scrollY, pageIndex, block, width: window.innerWidth, height: window.innerHeight, size: settings.size }));
  }
  function scrollToBlock(id) {
    const block = findBlock(id);
    if (!block) return false;
    window.scrollTo(0, Math.max(0, window.scrollY + block.getBoundingClientRect().top - $('.topbar').offsetHeight - 18));
    return true;
  }
  function pageForBlock(id) {
    const block = findBlock(id);
    if (!block || !block.getClientRects().length) return null;
    const left = block.getClientRects()[0].left - chapterEl.getBoundingClientRect().left + chapterEl.scrollLeft;
    return Math.max(0, Math.min(pageCount - 1, Math.floor((left + 2) / pageStep)));
  }
  function setPage(index) {
    pageIndex = Math.max(0, Math.min(pageCount - 1, index));
    chapterEl.scrollLeft = pageIndex * pageStep;
    $('#page-count').textContent = `第 ${pageIndex + 1} / ${pageCount} 页`;
    const sectionIndex = book.chapters.indexOf(currentSection);
    $('#page-prev').disabled = sectionIndex === 0 && pageIndex === 0;
    $('#page-next').disabled = sectionIndex === book.chapters.length - 1 && pageIndex === pageCount - 1;
    $('#page-prev-chapter').disabled = sectionIndex === 0;
    $('#page-next-chapter').disabled = sectionIndex === book.chapters.length - 1;
    savePosition();
  }
  function layoutPages(target = null) {
    if (settings.mode !== 'pages' || chapterEl.clientWidth < 1 || chapterEl.clientHeight < 1) return;
    const width = chapterEl.clientWidth;
    chapterEl.style.columnWidth = `${width}px`;
    for (const figure of chapterEl.querySelectorAll('.plate')) {
      const image = figure.querySelector('img'), caption = figure.querySelector('figcaption');
      image.style.maxHeight = `${Math.max(100, chapterEl.clientHeight - (caption?.offsetHeight || 0) - 64)}px`;
    }
    const gap = parseFloat(getComputedStyle(chapterEl).columnGap) || 0;
    pageStep = width + gap;
    pageCount = Math.max(1, Math.ceil((chapterEl.scrollWidth + gap - 1) / pageStep));
    let targetPage = pageIndex;
    if (target?.last || keepLastPage) targetPage = pageCount - 1;
    else if (typeof target?.page === 'number') targetPage = target.page;
    else if (target?.block != null) targetPage = pageForBlock(target.block) ?? targetPage;
    setPage(targetPage);
  }
  function scheduleLayout(target = null) {
    if (target) {
      const preservePage = layoutTarget && (layoutTarget.last || typeof layoutTarget.page === 'number');
      if (!preservePage || target.last || typeof target.page === 'number') layoutTarget = target;
    }
    cancelAnimationFrame(layoutFrame);
    layoutFrame = requestAnimationFrame(() => { const next = layoutTarget; layoutTarget = null; layoutPages(next); });
  }
  function render(id, target = {}) {
    const c = getChapter(id);
    currentSection = c; pageIndex = 0; pageCount = 1; keepLastPage = !!target.last; lastBlock = target.block ?? null;
    chapterEl.scrollLeft = 0;
    chapterEl.innerHTML = `${c.number === 1 ? bookOpening : ''}<div class="chapter-heading" data-block="-1"><div class="chapter-kicker">${c.label} · PDF 第 ${c.pdfPage} 页起</div><h1>${c.title}</h1></div>${c.html}`;
    $('#location').textContent = `${c.title} · PDF 第 ${c.pdfPage} 页起`;
    $('#source-link').href = `../../../走出戈壁-单伟健.pdf#page=${c.pdfPage}`;
    document.querySelectorAll('.toc-item').forEach(el => {
      const active = el.dataset.id === c.id;
      el.classList.toggle('active', active);
      if (active) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current');
    });
    const i = book.chapters.indexOf(c); $('#prev').disabled = i === 0; $('#next').disabled = i === book.chapters.length - 1;
    $('#prev').onclick = () => navigate(book.chapters[i - 1].id); $('#next').onclick = () => navigate(book.chapters[i + 1].id);
    if (settings.mode === 'pages') {
      window.scrollTo(0, 0);
      for (const image of chapterEl.querySelectorAll('img')) {
        image.loading = 'eager';
        image.addEventListener('load', () => { if (currentSection.id === c.id) scheduleLayout({ block: lastBlock, last: keepLastPage }); }, { once:true });
      }
      scheduleLayout(target);
      if (document.fonts?.ready) document.fonts.ready.then(() => { if (currentSection.id === c.id) scheduleLayout({ block: lastBlock, last: keepLastPage }); });
    } else {
      chapterEl.style.columnWidth = '';
      requestAnimationFrame(() => {
        if (target.block == null || !scrollToBlock(target.block)) window.scrollTo(0, target.y || 0);
        savePosition();
      });
    }
  }
  function navigate(id, target = {}) {
    if (currentId() === id) {
      if (settings.mode === 'pages') { keepLastPage = !!target.last; setPage(target.last ? pageCount - 1 : (target.page || 0)); }
      else window.scrollTo(0, 0);
      return;
    }
    pendingTarget = { id, ...target };
    location.hash = id;
  }
  function currentId() { return location.hash.slice(1); }
  function route() {
    const id = currentId() || book.chapters[0].id;
    const target = pendingTarget?.id === id ? pendingTarget : {};
    pendingTarget = null;
    render(id, target);
  }
  function moveChapter(delta, last = false) {
    const next = book.chapters[book.chapters.indexOf(currentSection) + delta];
    if (next) navigate(next.id, { last });
  }
  function movePage(delta) {
    keepLastPage = false;
    const next = pageIndex + delta;
    if (next < 0) moveChapter(-1, true);
    else if (next >= pageCount) moveChapter(1);
    else setPage(next);
  }
  window.addEventListener('hashchange', route); toc.addEventListener('click', e => {
    const b = e.target.closest('[data-id]');
    if (!b) return;
    navigate(b.dataset.id);
    if (window.matchMedia('(max-width:850px)').matches) { settings.tocOpen = false; applySettings(); saveSettings(); }
  });
  $('#toc-toggle').onclick = () => {
    const block = visibleBlock() ?? lastBlock;
    settings.tocOpen = !settings.tocOpen; applySettings(); saveSettings();
    if (settings.mode === 'pages') scheduleLayout({ block });
  };
  document.addEventListener('click', e => {
    if (window.matchMedia('(max-width:850px)').matches && settings.tocOpen && !e.target.closest('#toc-panel, #toc-toggle')) {
      settings.tocOpen = false; applySettings(); saveSettings();
    }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && settings.tocOpen && window.matchMedia('(max-width:850px)').matches && !$('#image-dialog').open) {
      settings.tocOpen = false; applySettings(); saveSettings(); $('#toc-toggle').focus();
    }
  });
  document.addEventListener('click', e => { const button = e.target.closest('.plate-button'); if (!button) return; $('#dialog-image').src = button.dataset.image; $('#dialog-image').alt = button.dataset.caption; $('#dialog-caption').textContent = button.dataset.caption; $('#image-dialog').showModal(); });
  $('#close-image').onclick = () => $('#image-dialog').close();
  $('#reading-mode').onchange = e => {
    const block = visibleBlock() ?? lastBlock;
    const y = window.scrollY;
    settings.mode = e.target.value; applySettings(); saveSettings();
    if (settings.mode === 'pages' && window.matchMedia('(max-width:850px)').matches) {
      settings.tocOpen = false; applySettings(); saveSettings();
    }
    render(currentSection.id, { block, y });
  };
  $('#page-prev').onclick = () => movePage(-1);
  $('#page-next').onclick = () => movePage(1);
  $('#page-prev-chapter').onclick = () => moveChapter(-1);
  $('#page-next-chapter').onclick = () => moveChapter(1);
  document.addEventListener('keydown', e => {
    if (settings.mode !== 'pages' || e.ctrlKey || e.altKey || e.metaKey || e.shiftKey || e.isComposing || $('#image-dialog').open || e.target.closest('input,textarea,select,[contenteditable]') || window.getSelection()?.toString()) return;
    const actions = { ArrowLeft: () => movePage(-1), ArrowRight: () => movePage(1), ArrowUp: () => moveChapter(-1), ArrowDown: () => moveChapter(1) };
    if (actions[e.key]) { e.preventDefault(); actions[e.key](); }
  });
  $('#font-down').onclick = () => {
    const block = visibleBlock() ?? lastBlock;
    settings.size = Math.max(15, settings.size - 1); applySettings(); saveSettings();
    if (settings.mode === 'pages') scheduleLayout({ block });
  };
  $('#font-up').onclick = () => {
    const block = visibleBlock() ?? lastBlock;
    settings.size = Math.min(28, settings.size + 1); applySettings(); saveSettings();
    if (settings.mode === 'pages') scheduleLayout({ block });
  };
  $('#theme').onclick = () => { settings.dark = !settings.dark; applySettings(); saveSettings(); };
  const results = $('#search-results'); $('#search').addEventListener('input', e => { const q = e.target.value.trim(); if (!q) { results.hidden = true; return; } const out = []; for (const c of book.chapters) { const at = c.searchText.indexOf(q); if (at >= 0) out.push({ c, excerpt: c.searchText.slice(Math.max(0,at-30), at+q.length+70) }); if (out.length >= 30) break; } results.innerHTML = out.length ? out.map(x => `<button class="result" data-id="${x.c.id}"><strong>${escapeHtml(x.c.title)}</strong>${escapeHtml(x.excerpt)}</button>`).join('') : '<div class="result">没有找到匹配内容。</div>'; results.hidden = false; });
  results.addEventListener('click', e => { const b = e.target.closest('[data-id]'); if (b) { $('#search').value = ''; results.hidden = true; navigate(b.dataset.id); } });
  window.addEventListener('scroll', () => { if (settings.mode === 'scroll') savePosition(); }, { passive:true });
  const saved = (() => { try { return JSON.parse(localStorage.getItem(positionKey)); } catch (_) { return null; } })();
  if (saved && book.chapters.some(c => c.id === saved.id) && (!currentId() || currentId() === saved.id)) {
    const sameLayout = saved.width === window.innerWidth && saved.height === window.innerHeight && saved.size === settings.size;
    pendingTarget = { id: saved.id, y: saved.y || 0, block: saved.block, page: settings.mode === 'pages' && sameLayout ? saved.pageIndex : undefined };
    if (currentId()) route(); else location.hash = saved.id;
  } else route();
})();
'''


if __name__ == "__main__":
    main()
