"""Build searchable, typeset Simplified and Traditional Chinese PDFs."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from PIL import Image as PILImage
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import B5
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Flowable, Image, PageBreak, PageTemplate,
    Paragraph,
)
from reportlab.platypus.tableofcontents import TableOfContents

from book_fonts import font_path
from export_common import (
    IMAGES, OUTPUT, Chapter, FrontMatter, expected_body_image_pages,
    image_pages, load_captions, load_chapters, load_frontmatter, reading_image,
)

# ASCII85 is only a transport encoding. Omitting it preserves the original
# image bytes and avoids inflating this image-heavy archival master.
rl_config.useA85 = 0

TITLE = "走出戈壁：我的中美故事"
PAGE_WIDTH, PAGE_HEIGHT = B5
LEFT = RIGHT = 44
TOP = BOTTOM = 48
FRAME_WIDTH = PAGE_WIDTH - LEFT - RIGHT
FRAME_HEIGHT = PAGE_HEIGHT - TOP - BOTTOM
MIN_PLATE_DPI = 100
TOC_NUMBER_WIDTH = 56
VERSE_INDENT = 21


def registered_font(script: str, role: str = "number") -> str:
    """Embed the explicit body/number, title, and lead-in font families."""
    name = f"Gobi-{script}-{role}"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, str(font_path(script, role))))
    return name


def toc_label(title: str, number_label: str, fonts: dict[str, str]) -> str:
    """Keep number/title families distinct and align the title column."""
    title_markup = f'<font name="{fonts["title"]}">{html.escape(title)}</font>'
    if not number_label:
        return title_markup
    size = 8.4
    remaining = TOC_NUMBER_WIDTH - pdfmetrics.stringWidth(number_label, fonts["number"], size)
    nbsp_width = pdfmetrics.stringWidth("\u00a0", fonts["number"], size)
    # Ordinary spaces are collapsed by Paragraph's parser; NBSP preserves
    # this measured padding. The residual error is at most half a space.
    padding = "&#160;" * max(0, round(remaining / nbsp_width))
    return f'<font name="{fonts["number"]}" size="{size}">{html.escape(number_label)}{padding}</font>{title_markup}'


class BookDocument(BaseDocTemplate):
    def __init__(self, filename: str, *, font: str, author: str):
        super().__init__(
            filename, pagesize=B5, leftMargin=LEFT, rightMargin=RIGHT,
            topMargin=TOP, bottomMargin=BOTTOM, title=TITLE, author=author,
            pageCompression=1,
        )
        self.body_font = font
        frame = Frame(LEFT, BOTTOM, FRAME_WIDTH, FRAME_HEIGHT,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="book", frames=[frame], onPage=self.draw_page))

    def draw_page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d6d1c8"))
        canvas.setLineWidth(0.5)
        canvas.line(LEFT, 33, PAGE_WIDTH - RIGHT, 33)
        canvas.setFont(self.body_font, 8)
        canvas.setFillColor(colors.HexColor("#6b6258"))
        # These are consecutive reading pages, independent of scan locators.
        canvas.drawCentredString(PAGE_WIDTH / 2, 21, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        entry = getattr(flowable, "_book_entry", None)
        if entry:
            key, label, markup = entry
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(label, key, level=0)
            self.notify("TOCEntry", (0, markup, self.page, key))


class SearchableScan(Flowable):
    """Preserve the original dedication with a searchable invisible layer."""

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
        text = self.canv.beginText()
        text.setTextOrigin(18, self.height - 24)
        text.setFont(self.font, 8)
        text.setLeading(11)
        text.setTextRenderMode(3)
        paragraphs = [self.section.title] + [block.value for block in self.section.blocks
                                               if block.kind in {"paragraph", "verse"}]
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


class ImagePlate(Flowable):
    """One complete reading page with an uncropped image and its captions."""

    def __init__(self, path: Path, captions: list[str], style: ParagraphStyle):
        super().__init__()
        self.path = Path(path)
        self.width, self.height = FRAME_WIDTH, FRAME_HEIGHT - 1
        self.paragraphs = [Paragraph(html.escape(value), style) for value in captions]
        self.caption_heights = [p.wrap(self.width, self.height)[1] for p in self.paragraphs]
        self.caption_gaps = [p.style.spaceAfter for p in self.paragraphs[:-1]]
        caption_height = sum(self.caption_heights) + sum(self.caption_gaps)
        self.gap = 9 if self.paragraphs else 0
        available_height = self.height - caption_height - self.gap
        if available_height <= 0:
            raise ValueError(f"Image captions exceed one page: {self.path}")
        with PILImage.open(self.path) as source:
            pixel_width, pixel_height = source.size
        # Preserve proportions and never enlarge past the minimum useful DPI.
        scale = min(self.width / pixel_width, available_height / pixel_height,
                    72 / MIN_PLATE_DPI)
        self.image_width = pixel_width * scale
        self.image_height = pixel_height * scale
        self.content_height = self.image_height + self.gap + caption_height
        self.hAlign = "CENTER"

    def draw(self):
        y = (self.height + self.content_height) / 2
        y -= self.image_height
        self.canv.drawImage(str(self.path), (self.width - self.image_width) / 2, y,
                           self.image_width, self.image_height)
        y -= self.gap
        for index, (paragraph, height) in enumerate(zip(self.paragraphs, self.caption_heights)):
            y -= height
            paragraph.drawOn(self.canv, 0, y)
            if index < len(self.caption_gaps):
                y -= self.caption_gaps[index]


def fit_image(path: Path, max_width: float, max_height: float) -> Image:
    with PILImage.open(path) as source:
        width, height = source.size
    ratio = min(max_width / width, max_height / height)
    result = Image(str(path), width=width * ratio, height=height * ratio)
    result.hAlign = "CENTER"
    return result


def styles(font: str, title_font: str | None = None,
           leadin_font: str | None = None) -> dict[str, ParagraphStyle]:
    title_font = title_font or font
    leadin_font = leadin_font or font
    result = {
        "chapter": ParagraphStyle(
            "chapter", fontName=title_font, fontSize=17, leading=26, alignment=TA_CENTER,
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
    result["lead-in"] = ParagraphStyle(
        "lead-in", parent=result["body"], fontName=leadin_font,
        fontSize=10, leading=17, firstLineIndent=20,
    )
    result["front-title"] = ParagraphStyle(
        "front-title", parent=result["chapter"], fontName=font, spaceBefore=0, spaceAfter=22,
    )
    result["front-body"] = ParagraphStyle(
        "front-body", parent=result["body"], fontSize=10.2, firstLineIndent=20.4,
    )
    for role in ("body", "lead-in"):
        for alignment, value in (("left", TA_LEFT), ("center", TA_CENTER)):
            result[f"verse-{role}-{alignment}"] = ParagraphStyle(
                f"verse-{role}-{alignment}", parent=result[role], alignment=value,
                firstLineIndent=0, leftIndent=2 * result[role].fontSize,
                rightIndent=2 * result[role].fontSize,
                spaceBefore=7, spaceAfter=10,
            )
    return result


def page_break(story: list) -> None:
    """Never create a blank page between adjacent chapter/plate breaks."""
    if story and not isinstance(story[-1], PageBreak):
        story.append(PageBreak())


def add_verse(story: list, block, style: dict[str, ParagraphStyle]) -> None:
    """Preserve authored lines/stanzas without ordinary first-line indents."""
    role = getattr(block, "role", "body")
    alignment = getattr(block, "alignment", "left")
    verse_style = style[f"verse-{role}-{alignment}"]
    # ReportLab handles a paragraph taller than a page, preserving the same
    # indentation on continuation pages. Two explicit breaks retain a stanza.
    markup = html.escape(block.value).replace("\n", "<br/>")
    story.append(Paragraph(markup, verse_style))


def add_chapter(story: list, chapter: Chapter, chapter_index: int,
                captions: dict[int, list[str]], style: dict[str, ParagraphStyle],
                fonts: dict[str, str] | None = None) -> None:
    if chapter_index > 1:
        page_break(story)
    fonts = fonts or {"number": style["body"].fontName, "title": style["chapter"].fontName}
    number_label = getattr(chapter, "number_label", "")
    label = getattr(chapter, "label", chapter.title)
    markup = html.escape(chapter.title)
    if number_label:
        markup = f'<font name="{fonts["number"]}" size="12">{html.escape(number_label)}</font><br/>{markup}'
    heading = Paragraph(markup, style["chapter"])
    heading._is_chapter = True
    heading._book_entry = (f"chapter-{chapter_index:02d}", label,
                           toc_label(chapter.title, number_label, fonts))
    story.append(heading)
    for block in chapter.blocks:
        if block.kind == "paragraph":
            paragraph_style = style[getattr(block, "role", "body")]
            story.append(Paragraph(html.escape(block.value).replace("\n", "<br/>"), paragraph_style))
        elif block.kind == "verse":
            add_verse(story, block, style)
        elif block.kind == "break":
            story.append(Paragraph("★★★", style["break"]))
        elif block.kind == "image":
            page_break(story)
            page = int(block.value[5:8])
            story.append(ImagePlate(reading_image(block.value), captions.get(page, []), style["caption"]))
            page_break(story)
        else:
            raise ValueError(f"Unsupported book block: {block.kind}")


def validate_glyphs(frontmatter, chapters, captions, fonts) -> None:
    """Check each character against the actual font assigned to its role."""
    texts = {"number": TITLE + "目录目錄★★★0123456789", "title": "", "lead-in": ""}
    for part in frontmatter:
        texts["number"] += part.title + "".join(b.value for b in part.blocks)
        texts["title"] += part.title
    for chapter in chapters:
        texts["number"] += getattr(chapter, "number_label", "")
        texts["title"] += chapter.title
        for block in chapter.blocks:
            if block.kind in {"paragraph", "verse"}:
                role = "lead-in" if getattr(block, "role", "body") == "lead-in" else "number"
                texts[role] += block.value
    texts["number"] += "".join(value for values in captions.values() for value in values)
    for role, text in texts.items():
        glyphs = pdfmetrics.getFont(fonts[role]).face.charToGlyph
        missing = sorted({char for char in text if not char.isspace() and ord(char) not in glyphs})
        if missing:
            raise ValueError(f"The {role} PDF font is missing glyphs: {''.join(missing)}")


def build_one(script: str) -> Path:
    chapters = load_chapters(script)
    frontmatter = load_frontmatter(script)
    captions = load_captions(script)
    assert len(chapters) == 33
    assert image_pages(chapters) == expected_body_image_pages(), "Chapter image plates do not match the image manifest"
    fonts = {role: registered_font(script, role) for role in ("number", "title", "lead-in")}
    validate_glyphs(frontmatter, chapters, captions, fonts)
    style = styles(fonts["number"], fonts["title"], fonts["lead-in"])
    author = "单伟建" if script == "simplified" else "單偉建"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f"走出戈壁-{'简体' if script == 'simplified' else '繁体'}.pdf"
    document = BookDocument(str(target), font=fonts["number"], author=author)
    toc = TableOfContents()
    toc.levelStyles = [style["toc-entry"]]
    toc.dotsMinLevel = 0
    story = [fit_image(IMAGES / "page-001.jpg", FRAME_WIDTH, FRAME_HEIGHT), PageBreak(),
             fit_image(IMAGES / "page-002.jpg", FRAME_WIDTH, FRAME_HEIGHT), PageBreak()]
    for part in frontmatter:
        entry = (f"front-{part.slug}", part.title, toc_label(part.title, "", fonts))
        if getattr(part, "presentation", "scan") == "text":
            heading = Paragraph(html.escape(part.title), style["front-title"])
            heading._book_entry = entry
            story.append(heading)
            for block in part.blocks:
                if block.kind == "paragraph":
                    story.append(Paragraph(html.escape(block.value).replace("\n", "<br/>"), style["front-body"]))
        else:
            scan = SearchableScan(part, fonts["number"])
            scan._book_entry = entry
            story.append(scan)
        page_break(story)
    story.extend([Paragraph("目录" if script == "simplified" else "目錄", style["toc-title"]), toc, PageBreak()])
    for index, chapter in enumerate(chapters, 1):
        add_chapter(story, chapter, index, captions, style, fonts)
    while story and isinstance(story[-1], PageBreak):
        story.pop()
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
