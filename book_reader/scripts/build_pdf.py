"""Build searchable, typeset Simplified and Traditional Chinese PDFs."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import B5
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents

from export_common import IMAGES, OUTPUT, Chapter, image_pages, load_captions, load_chapters


TITLE = "走出戈壁：我的中美故事"
PAGE_WIDTH, PAGE_HEIGHT = B5
LEFT = RIGHT = 44
TOP = 48
BOTTOM = 48
FRAME_WIDTH = PAGE_WIDTH - LEFT - RIGHT
FRAME_HEIGHT = PAGE_HEIGHT - TOP - BOTTOM


def registered_font(script: str) -> str:
    name = "NotoSC" if script == "simplified" else "NotoTC"
    filename = "NotoSansSC-VF.ttf" if script == "simplified" else "NotoSansTC-VF.ttf"
    path = Path("C:/Windows/Fonts") / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required Chinese font: {path}")
    pdfmetrics.registerFont(TTFont(name, str(path)))
    return name


class BookDocument(BaseDocTemplate):
    def __init__(self, filename: str, *, font: str, author: str):
        super().__init__(
            filename,
            pagesize=B5,
            leftMargin=LEFT,
            rightMargin=RIGHT,
            topMargin=TOP,
            bottomMargin=BOTTOM,
            title=TITLE,
            author=author,
            pageCompression=1,
        )
        self.body_font = font
        frame = Frame(LEFT, BOTTOM, FRAME_WIDTH, FRAME_HEIGHT, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="book", frames=[frame], onPage=self.draw_page))
        self.chapter_number = 0

    def beforeDocument(self):
        self.chapter_number = 0

    def draw_page(self, canvas, doc):
        if doc.page <= 2:
            return
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d6d1c8"))
        canvas.setLineWidth(0.5)
        canvas.line(LEFT, 33, PAGE_WIDTH - RIGHT, 33)
        canvas.setFont(self.body_font, 8)
        canvas.setFillColor(colors.HexColor("#6b6258"))
        canvas.drawCentredString(PAGE_WIDTH / 2, 21, str(doc.page - 2))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and getattr(flowable, "_is_chapter", False):
            self.chapter_number += 1
            title = flowable.getPlainText()
            key = f"chapter-{self.chapter_number:02d}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=0)
            self.notify("TOCEntry", (0, title, self.page - 2, key))


def fit_image(path: Path, max_width: float, max_height: float) -> Image:
    with PILImage.open(path) as source:
        width, height = source.size
    ratio = min(max_width / width, max_height / height)
    result = Image(str(path), width=width * ratio, height=height * ratio)
    result.hAlign = "CENTER"
    return result


def styles(font: str) -> dict[str, ParagraphStyle]:
    return {
        "chapter": ParagraphStyle(
            "chapter", fontName=font, fontSize=17, leading=26, alignment=TA_CENTER,
            spaceBefore=48, spaceAfter=32, wordWrap="CJK", textColor=colors.HexColor("#25211d"),
        ),
        "body": ParagraphStyle(
            "body", fontName=font, fontSize=10.5, leading=17.3, alignment=TA_JUSTIFY,
            firstLineIndent=21, spaceAfter=7, wordWrap="CJK", allowWidows=0, allowOrphans=0,
            textColor=colors.HexColor("#25211d"),
        ),
        "caption": ParagraphStyle(
            "caption", fontName=font, fontSize=8.2, leading=12.7, alignment=TA_LEFT,
            spaceAfter=3, wordWrap="CJK", textColor=colors.HexColor("#5e554b"),
        ),
        "break": ParagraphStyle(
            "break", fontName=font, fontSize=11, leading=18, alignment=TA_CENTER,
            spaceBefore=7, spaceAfter=15,
        ),
        "toc-title": ParagraphStyle(
            "toc-title", fontName=font, fontSize=18, leading=25, alignment=TA_CENTER,
            spaceBefore=35, spaceAfter=25,
        ),
        "toc-entry": ParagraphStyle(
            "toc-entry", fontName=font, fontSize=10.5, leading=20,
            leftIndent=12, firstLineIndent=0, rightIndent=15,
        ),
    }


def add_chapter(story: list, chapter: Chapter, chapter_index: int, captions: dict[int, list[str]], style: dict[str, ParagraphStyle]) -> None:
    if chapter_index > 1:
        story.append(PageBreak())
    heading = Paragraph(html.escape(chapter.title), style["chapter"])
    heading._is_chapter = True
    story.append(heading)
    for block in chapter.blocks:
        if block.kind == "paragraph":
            story.append(Paragraph(html.escape(block.value), style["body"]))
        elif block.kind == "break":
            story.append(Paragraph("★★★", style["break"]))
        else:
            page = int(block.value[5:8])
            page_captions = captions.get(page, [])
            # Caption text remains searchable; the source plate also retains its
            # original typography and any captions not reliably transcribed.
            max_image_height = FRAME_HEIGHT * (0.65 if page_captions else 0.78)
            figure = [Spacer(1, 15), fit_image(IMAGES / block.value, FRAME_WIDTH, max_image_height)]
            if page_captions:
                figure.append(Spacer(1, 7))
                figure.extend(Paragraph(html.escape(value), style["caption"]) for value in page_captions)
            figure.append(Spacer(1, 12))
            story.append(KeepTogether(figure))


def build_one(script: str) -> Path:
    chapters = load_chapters(script)
    captions = load_captions(script)
    assert len(chapters) == 33
    assert len(image_pages(chapters)) == 19
    font = registered_font(script)
    style = styles(font)
    author = "单伟建" if script == "simplified" else "單偉建"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f"走出戈壁-{'简体' if script == 'simplified' else '繁体'}.pdf"
    document = BookDocument(str(target), font=font, author=author)
    toc = TableOfContents()
    toc.levelStyles = [style["toc-entry"]]
    toc.dotsMinLevel = 0
    story = [
        fit_image(IMAGES / "page-001.jpg", FRAME_WIDTH, FRAME_HEIGHT),
        PageBreak(),
        fit_image(IMAGES / "page-002.jpg", FRAME_WIDTH, FRAME_HEIGHT),
        PageBreak(),
        Paragraph("目录" if script == "simplified" else "目錄", style["toc-title"]),
        toc,
        PageBreak(),
    ]
    for index, chapter in enumerate(chapters, 1):
        add_chapter(story, chapter, index, captions, style)
    document.multiBuild(story, maxPasses=4)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", choices=["simplified", "traditional", "both"], default="both")
    args = parser.parse_args()
    for script in ([args.script] if args.script != "both" else ["simplified", "traditional"]):
        print(build_one(script), flush=True)


if __name__ == "__main__":
    main()
