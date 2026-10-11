"""Build reflowable EPUB 3 books from the chapter reading manuscripts."""

from __future__ import annotations

import argparse
import html
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from book_fonts import font_assets, font_css
from export_common import OUTPUT, Chapter, FrontMatter, expected_body_image_pages, image_pages, load_captions, load_chapters, load_frontmatter, reading_image


TITLE = "走出戈壁：我的中美故事"
CSS = """@charset "utf-8";
html { writing-mode: horizontal-tb; }
body { font-family: serif; line-height: 1.7; margin: 0 5%; color: #24211d; }
h1 { font-size: 1.55em; line-height: 1.45; text-align: center; margin: 2.5em 0 1.8em; }
p { margin: 0 0 .85em; text-indent: 2em; text-align: justify; }
figure { margin: 1.8em 0; text-align: center; break-inside: avoid; break-before: page; break-after: page; page-break-before: always; page-break-after: always; }
figure img { display: block; max-width: 100%; max-height: 90vh; margin: auto; object-fit: contain; }
figcaption { font-size: .82em; line-height: 1.5; margin-top: .7em; text-align: left; }
figcaption span { display: block; margin-bottom: .35em; }
.scene-break { text-align: center; margin: 1.5em 0; letter-spacing: .5em; }
.cover { margin: 0; text-align: center; }
.cover img { display: block; width: 100%; max-height: 100vh; object-fit: contain; }
.nav-list { line-height: 1.6; list-style: none; padding: 0; }
.nav-list li { margin: .7em 0; }
.nav-list a { text-decoration: none; }
.toc-num { font-family: "GobiChapterNumber", sans-serif; font-size: .78em; font-weight: 400; margin-right: 1em; white-space: nowrap; }
.toc-label, h1 { font-family: "GobiChapterTitle", serif; font-weight: 400; }
.toc-label { font-size: 1.1em; }
h1 .chapter-num { display: block; font-family: "GobiChapterNumber", sans-serif; font-size: .62em; font-weight: 400; margin-bottom: .7em; }
p.lead-in { font-family: "GobiLeadIn", serif; font-size: 95%; font-style: normal; font-weight: 300; }
p.verse { text-indent: 0; text-align: left; white-space: normal; overflow-wrap: anywhere; }
p.verse-left { margin-inline-start: 2em; }
p.verse-center { text-align: center; margin-inline: 0; }
.front-scan { break-after: page; }
.front-scan img { max-height: 92vh; }
.dedication p { text-align: center; text-indent: 0; margin-top: 3em; }
p.signature { text-indent: 0; text-align: right; break-inside: avoid; page-break-inside: avoid; }
"""


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def xhtml(title: str, language: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{language}" lang="{language}">'
        '<head><meta charset="utf-8"/>'
        f'<title>{escape(title)}</title><link rel="stylesheet" href="styles.css"/></head>'
        f'<body>{body}</body></html>'
    )


def paragraph_xhtml(block) -> str:
    """Preserve semantic styling and every explicitly authored line break."""
    classes = []
    if block.role == "lead-in":
        classes.append("lead-in")
    if block.kind == "verse":
        classes.extend(("verse", f"verse-{block.alignment}"))
    elif block.kind == "signature":
        classes.append("signature")
    attributes = f' class="{" ".join(classes)}"' if classes else ""
    return f'<p{attributes}>{escape(block.value).replace(chr(10), "<br/>")}</p>'


def chapter_xhtml(chapter: Chapter, language: str, captions: dict[int, list[str]]) -> str:
    number = f'<span class="chapter-num">{escape(chapter.number_label)}</span>' if chapter.number else ""
    body = [f'<h1>{number}<span class="chapter-title">{escape(chapter.title)}</span></h1>']
    for block in chapter.blocks:
        if block.kind in {"paragraph", "verse", "signature"}:
            body.append(paragraph_xhtml(block))
        elif block.kind == "break":
            body.append('<div class="scene-break" aria-label="段落分隔">★★★</div>')
        elif block.kind == "image":
            page = int(block.value[5:8])
            captions_html = "".join(f'<span>{escape(value)}</span>' for value in captions.get(page, []))
            caption = f'<figcaption>{captions_html}</figcaption>' if captions_html else ""
            body.append(
                f'<figure><img src="images/{block.value}" alt="原书第 {page} 页图片"/>'
                f'{caption}</figure>'
            )
        else:
            raise ValueError(f"Unsupported block kind: {block.kind}")
    return xhtml(chapter.label, language, "\n".join(body))


def frontmatter_xhtml(section: FrontMatter, language: str) -> str:
    transcription = "".join(
        paragraph_xhtml(block) for block in section.blocks
        if block.kind in {"paragraph", "verse", "signature"}
    )
    scan = (
        f'<figure class="front-scan"><img src="images/{section.image.name}" '
        f'alt="{escape(section.title)}原页，PDF 第 {section.source_page} 页"/></figure>'
    ) if section.presentation == "scan" else ""
    body = scan + f'<section class="{section.layout}"><h1>{escape(section.title)}</h1>{transcription}</section>'
    return xhtml(section.title, language, body)


def build_one(script: str) -> Path:
    chapters = load_chapters(script)
    frontmatter = load_frontmatter(script)
    captions = load_captions(script)
    fonts = font_assets(script, chapters, frontmatter)
    assert len(chapters) == 33
    assert image_pages(chapters) == expected_body_image_pages(), "Chapter image plates do not match the image manifest"
    language = "zh-CN" if script == "simplified" else "zh-TW"
    author = "单伟建" if script == "simplified" else "單偉建"
    output_name = f"走出戈壁-{'简体' if script == 'simplified' else '繁体'}.epub"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / output_name
    cover = "page-001.jpg"
    title_image = "page-002.jpg"
    picture_names = [cover, title_image] + sorted({f"page-{page:03d}.jpg" for page in image_pages(chapters)})
    for name in picture_names:
        if not reading_image(name).is_file():
            raise FileNotFoundError(reading_image(name))

    nav_entries = [(f"front-{part.slug}.xhtml", "", part.title, part.title) for part in frontmatter]
    nav_entries += [(f"chapter-{i:02d}.xhtml", chapter.number_label, chapter.title, chapter.label) for i, chapter in enumerate(chapters, 1)]
    nav_links = "".join(
        f'<li><a href="{href}">'
        + (f'<span class="toc-num">{escape(number)}</span>' if number else "")
        + f'<span class="toc-label">{escape(title)}</span></a></li>'
        for href, number, title, label in nav_entries
    )
    nav = xhtml("目录", language, f'<nav epub:type="toc" id="toc" xmlns:epub="http://www.idpf.org/2007/ops"><h1>目录</h1><ol class="nav-list">{nav_links}</ol></nav>')
    ncx_items = "".join(
        f'<navPoint id="entry-{i:02d}" playOrder="{i}"><navLabel><text>{escape(label)}</text></navLabel><content src="{href}"/></navPoint>'
        for i, (href, number, title, label) in enumerate(nav_entries, 1)
    )
    ncx = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        f'<head><meta name="dtb:uid" content="urn:book:walk-out-of-the-gobi:{script}"/></head>'
        f'<docTitle><text>{escape(TITLE)}</text></docTitle><navMap>{ncx_items}</navMap></ncx>'
    )
    manifest = [
        '<item id="css" href="styles.css" media-type="text/css"/>',
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
        '<item id="title-page" href="title.xhtml" media-type="application/xhtml+xml"/>',
    ]
    manifest.extend(
        f'<item id="front-{part.slug}" href="front-{part.slug}.xhtml" media-type="application/xhtml+xml"/>'
        for part in frontmatter
    )
    manifest.extend(
        f'<item id="front-image-{part.slug}" href="images/{part.image.name}" media-type="image/png"/>'
        for part in frontmatter if part.presentation == "scan"
    )
    manifest.extend(
        f'<item id="chapter-{i:02d}" href="chapter-{i:02d}.xhtml" media-type="application/xhtml+xml"/>'
        for i in range(1, len(chapters) + 1)
    )
    manifest.extend(
        f'<item id="image-{i:02d}" href="images/{name}" media-type="image/jpeg"'
        + (' properties="cover-image"' if name == cover else '') + '/>'
        for i, name in enumerate(picture_names, 1)
    )
    manifest.extend(
        f'<item id="font-asset-{i}" href="fonts/{name}" media-type="{("font/ttf" if name.endswith(".ttf") else "text/plain")}"/>'
        for i, name in enumerate(fonts, 1)
    )
    spine = '<itemref idref="cover-page"/><itemref idref="title-page"/>'
    spine += "".join(f'<itemref idref="front-{part.slug}"/>' for part in frontmatter)
    spine += '<itemref idref="nav"/>'
    spine += "".join(
        f'<itemref idref="chapter-{i:02d}"/>' for i in range(1, len(chapters) + 1)
    )
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="'
        + language + '"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="book-id">urn:book:walk-out-of-the-gobi:{script}</dc:identifier>'
        f'<dc:title>{escape(TITLE)}</dc:title><dc:creator>{escape(author)}</dc:creator>'
        f'<dc:language>{language}</dc:language>'
        '<meta property="dcterms:modified">'
        + datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        + '</meta></metadata><manifest>' + ''.join(manifest) + '</manifest>'
        '<spine toc="ncx">' + spine + '</spine></package>'
    )
    container = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        '</rootfiles></container>'
    )
    with zipfile.ZipFile(target, "w") as book:
        book.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        book.writestr("META-INF/container.xml", container)
        book.writestr("OEBPS/styles.css", CSS.replace('@charset "utf-8";', '@charset "utf-8";\n' + font_css()))
        for name, data in fonts.items():
            book.writestr(f"OEBPS/fonts/{name}", data, compress_type=zipfile.ZIP_DEFLATED)
        book.writestr("OEBPS/nav.xhtml", nav)
        book.writestr("OEBPS/toc.ncx", ncx)
        book.writestr("OEBPS/content.opf", opf)
        book.writestr("OEBPS/cover.xhtml", xhtml(TITLE, language, f'<div class="cover"><img src="images/{cover}" alt="原书封面"/></div>'))
        book.writestr("OEBPS/title.xhtml", xhtml("题字", language, f'<div class="cover"><img src="images/{title_image}" alt="原书题字页"/></div>'))
        for part in frontmatter:
            book.writestr(f"OEBPS/front-{part.slug}.xhtml", frontmatter_xhtml(part, language))
            if part.presentation == "scan":
                book.write(part.image, f"OEBPS/images/{part.image.name}", compress_type=zipfile.ZIP_STORED)
        for i, chapter in enumerate(chapters, 1):
            book.writestr(f"OEBPS/chapter-{i:02d}.xhtml", chapter_xhtml(chapter, language, captions))
        for name in picture_names:
            book.write(reading_image(name), f"OEBPS/images/{name}", compress_type=zipfile.ZIP_STORED)
    # Parse every authored XML/XHTML entry, including the navigation and metadata.
    with zipfile.ZipFile(target) as book:
        for name in book.namelist():
            if name.endswith((".xml", ".opf", ".xhtml", ".ncx")):
                ET.fromstring(book.read(name))
        assert book.testzip() is None
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", choices=["simplified", "traditional", "both"], default="both")
    args = parser.parse_args()
    for script in ([args.script] if args.script != "both" else ["simplified", "traditional"]):
        print(build_one(script))


if __name__ == "__main__":
    main()
