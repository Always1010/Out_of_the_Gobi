"""Build and validate the introduction and reader for GitHub Pages."""

from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

import build_reader_site

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "_site"
DEFAULT_URL = "https://always1010.github.io/Out_of_the_Gobi/"


class References(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        for key, value in attrs:
            if key in {"href", "src", "data-image"} and value:
                self.urls.append(value)


def check_reference(site: Path, parent: Path, url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return
    path = (parent / unquote(parsed.path)).resolve()
    if not path.is_relative_to(site.resolve()):
        raise ValueError(f"Reference escapes the published site: {url}")
    if path.is_dir():
        path /= "index.html"
    if not path.is_file():
        raise FileNotFoundError(f"Missing published asset: {url} (from {parent})")


def validate_site(site: Path) -> None:
    for page in (site / "index.html", site / "read/index.html"):
        source = page.read_text(encoding="utf-8")
        if "__SITE_URL__" in source or "__GOOGLE_VERIFICATION__" in source:
            raise ValueError(f"Unresolved homepage metadata in {page}")
        parser = References()
        parser.feed(source)
        for url in parser.urls:
            check_reference(site, page.parent, url)
    reader_page = (site / "read/index.html").read_text(encoding="utf-8")
    if (site / "read/images/page-001.jpg").exists() or "images/page-001.jpg" in (site / "read/app.js").read_text(encoding="utf-8"):
        raise ValueError("The online site must not publish or display the book cover")
    if 'data-online="true"' not in reader_page or 'id="source-link" href="../"' not in reader_page:
        raise ValueError("Published reader must use online navigation")
    for data_file in (site / "read").glob("data-*.js"):
        data = data_file.read_text(encoding="utf-8")
        book = json.loads(data.removeprefix("window.BOOK = ").strip().removesuffix(";"))
        parser = References()
        for chapter in book["chapters"]:
            parser.feed(chapter["html"])
        for url in parser.urls:
            check_reference(site, site / "read", url)
    for sheet in site.rglob("*.css"):
        for url in re.findall(r'url\([\"\']?([^\"\')]+)[\"\']?\)', sheet.read_text(encoding="utf-8")):
            check_reference(site, sheet.parent, url)
    files = list(site.rglob("*"))
    if any(path.is_symlink() or path.suffix.lower() in {".pdf", ".epub"} for path in files):
        raise ValueError("The Pages artifact must not contain links or ebook files")
    size = sum(path.stat().st_size for path in files if path.is_file())
    if size > 1024 ** 3:
        raise ValueError("Published site exceeds the GitHub Pages 1 GB limit")
    ET.parse(site / "sitemap.xml")
    print(f"Validated published links, chapter images, fonts and sitemap ({size / 1024 ** 2:.1f} MiB)")


def main(site_url: str = DEFAULT_URL, google_verification: str = "") -> None:
    parsed = urlsplit(site_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("Site URL must be an absolute HTTPS URL without query, fragment or credentials")
    site_url = site_url.rstrip("/") + "/"
    # Only ever replace this checkout's fixed generated directory.
    if SITE.is_symlink() or SITE.resolve() != ROOT.resolve() / "_site":
        raise ValueError("Unsafe Pages output directory")
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    build_reader_site.main(online=True, output_dir=SITE / "read")
    template = (ROOT / "web/index.html").read_text(encoding="utf-8")
    verification = (
        f'<meta name="google-site-verification" content="{html.escape(google_verification, quote=True)}">'
        if google_verification else ""
    )
    homepage = template.replace("__SITE_URL__", html.escape(site_url, quote=True)).replace("__GOOGLE_VERIFICATION__", verification)
    (SITE / "index.html").write_text(homepage, encoding="utf-8")
    shutil.copy2(ROOT / "web/styles.css", SITE / "styles.css")
    reader = SITE / "read/index.html"
    source = reader.read_text(encoding="utf-8").replace(
        "</head>", f'<link rel="canonical" href="{html.escape(site_url + "read/", quote=True)}">\n</head>'
    )
    reader.write_text(source, encoding="utf-8")
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    sitemap = ET.Element(f"{{{namespace}}}urlset")
    for suffix in ("", "read/"):
        item = ET.SubElement(sitemap, f"{{{namespace}}}url")
        ET.SubElement(item, f"{{{namespace}}}loc").text = site_url + suffix
    ET.ElementTree(sitemap).write(SITE / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (SITE / ".nojekyll").touch()
    validate_site(SITE)
    print(f"Built {site_url} in {SITE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", default=DEFAULT_URL, help="Public Pages base URL including repository path")
    parser.add_argument("--google-verification", default="", help="Optional Search Console verification token")
    args = parser.parse_args()
    main(args.site_url, args.google_verification)
