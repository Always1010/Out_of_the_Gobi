"""Build searchable, typeset Simplified and Traditional Chinese PDFs."""

from __future__ import annotations

import argparse
import html
import os
from io import BytesIO
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
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents

from export_common import IMAGES, OUTPUT, Chapter, FrontMatter, expected_body_image_pages, image_pages, load_captions, load_chapters, load_frontmatter


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
    override = os.environ.get("GOBI_FONT_SC" if script == "simplified" else "GOBI_FONT_TC")
    candidates = [Path(override)] if override else [
        Path("C:/Windows/Fonts") / filename,
        Path("/usr/share/fonts/truetype/noto") / filename,
        Path.home() / ".local/share/fonts" / filename,
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ]
    for path in candidates:
        if path.is_file():
            pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
    if override:
        raise FileNotFoundError(f"Configured Chinese TrueType font not found: {override}")
    # PyMuPDF ships a portable Chinese TrueType font. ReportLab cannot embed
    # the CFF outlines used by typical Linux Noto CJK .ttc installations.
    try:
        import fitz
    except ModuleNotFoundError:
        raise RuntimeError(
            "Install PyMuPDF for an embedded Chinese font, or set GOBI_FONT_SC/GOBI_FONT_TC "
            "to a Chinese TrueType font."
        ) from None
    pdfmetrics.registerFont(TTFont(name, BytesIO(fitz.Font("cjk").buffer)))
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
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d6d1c8"))
        canvas.setLineWidth(0.5)
        canvas.line(LEFT, 33, PAGE_WIDTH - RIGHT, 33)
        canvas.setFont(self.body_font, 8)
        canvas.setFillColor(colors.HexColor("#6b6258"))
        # Number the reading PDF consecutively; scan/printed page jumps are
        # source locators and must never create gaps in the reflowed book.
        canvas.drawCentredString(PAGE_WIDTH / 2, 21, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, SearchableScan):
            key = f"front-{flowable.section.slug}"
            title = flowable.section.title
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=0)
            self.notify("TOCEntry", (0, title, self.page, key))
        if isinstance(flowable, Paragraph) and getattr(flowable, "_is_chapter", False):
            self.chapter_number += 1
            title = flowable.getPlainText()
            key = f"chapter-{self.chapter_number:02d}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=0)
            self.notify("TOCEntry", (0, title, self.page, key))


class SearchableScan(Flowable):
    """Preserve the full original page, with a same-page searchable text layer."""

    def __init__(self, section: FrontMatter, font: str):
        super().__init__()
        self.section, self.font = section, font
        with PILImage.open(section.image) as source:
            width, height = source.size
        scale = min(FRAME_WIDTH / width, (FRAME_HEIGHT - 1) / height)
        self.width, self.height = width * scale, height * scale
        self.hAlign = "CENTER"

    def draw(self):
        self.canv.saveState()
        self.canv.drawImage(str(self.section.image), 0, 0, self.width, self.height)
        # These transparent lines enable text selection/search without adding
        # a second visible transcription to the dedication or its whitespace.
        text = self.canv.beginText()
        text.setTextOrigin(18, self.height - 24)
        text.setFont(self.font, 8)
        text.setLeading(11)
        text.setTextRenderMode(3)
        paragraphs = [self.section.title] + [block.value for block in self.section.blocks if block.kind == "paragraph"]
        for paragraph in paragraphs:
            for source_line in paragraph.split("\n"):
                line = ""
                for char in source_line:
                    if pdfmetrics.stringWidth(line + char, self.font, 8) > self.width - 36:
                        text.textLine(line)
                        line = ""
                    line += char
                if line:
                    text.textLine(line)
            text.textLine("")
        self.canv.drawText(text)
        self.canv.restoreState()


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
            story.append(Paragraph(html.escape(block.value).replace("\n", "<br/>"), style["body"]))
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
    frontmatter = load_frontmatter(script)
    captions = load_captions(script)
    assert len(chapters) == 33
    assert image_pages(chapters) == expected_body_image_pages(), "Chapter image plates do not match the image manifest"
    font = registered_font(script)
    contents = TITLE + "".join(part.title + "".join(block.value for block in part.blocks) for part in [*frontmatter, *chapters])
    contents += "".join(value for values in captions.values() for value in values)
    glyphs = pdfmetrics.getFont(font).face.charToGlyph
    missing = sorted({char for char in contents if not char.isspace() and ord(char) not in glyphs})
    if missing:
        raise ValueError(f"The PDF font is missing glyphs: {''.join(missing)}; configure GOBI_FONT_SC/GOBI_FONT_TC")
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
    ]
    for part in frontmatter:
        story.extend([SearchableScan(part, font), PageBreak()])
    story.extend([Paragraph("目录" if script == "simplified" else "目錄", style["toc-title"]), toc, PageBreak()])
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
