"""Runtime inputs must not leak machine paths into portable reader outputs."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import book_fonts
import build_reader_site as reader
from build_review_pdf import build_review_one
import fitz


class FontPathsTests(unittest.TestCase):
    def test_explicit_overrides_and_directory_for_both_scripts(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            for suffix, script in (("SC", "simplified"), ("TC", "traditional")):
                for role, key, filename in (
                    ("number", "GOBI_FONT", f"NotoSans{suffix}-Regular.ttf"),
                    ("title", "GOBI_SERIF", f"NotoSerif{suffix}-Regular.ttf"),
                    ("lead-in", "GOBI_LEADIN", "LXGWWenKai-Light.ttf"),
                ):
                    font = root / filename
                    font.touch()
                    with patch.dict(os.environ, {"GOBI_FONT_DIR": str(root)}):
                        self.assertEqual(book_fonts.font_path(script, role), font)
                    override = root / "custom.ttf"
                    override.touch()
                    with patch.dict(os.environ, {f"{key}_{suffix}": str(override), "GOBI_FONT_DIR": str(root)}):
                        self.assertEqual(book_fonts.font_path(script, role), override)

    def test_override_parent_and_repository_fallback(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            title = root / "NotoSerifSC-Regular.ttf"
            title.touch()
            with patch.dict(os.environ, {"GOBI_FONT_SC": str(root / "custom.ttf")}):
                self.assertEqual(book_fonts.font_path("simplified", "title"), title)
            with patch.object(book_fonts, "FONT_LICENSES", root):
                self.assertEqual(book_fonts.font_path("simplified", "title"), title)
                title.unlink()
                with self.assertRaisesRegex(FileNotFoundError, "GOBI_FONT_DIR"):
                    book_fonts.font_path("simplified", "title")
            with patch.dict(os.environ, {"GOBI_FONT_SC": str(root / "missing.ttf")}):
                with self.assertRaises(FileNotFoundError):
                    book_fonts.font_path("simplified")


class ReaderPathsTests(unittest.TestCase):
    def test_relative_url_custom_output_encoding_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = root / "原书 #?%.pdf"
            source.touch()
            output = root / "custom" / "reader"
            with patch.dict(os.environ, {"GOBI_SOURCE_PDF": str(source)}):
                url = reader.source_pdf_url(None, output)
                self.assertEqual((output / unquote(url)).resolve(), source)
                self.assertNotIn(str(root), url)
                self.assertIn("%23", url)
                self.assertIsNone(reader.source_pdf_url(root / "absent.pdf", output))
            self.assertIsNone(reader.source_pdf_url(None, output))
            self.assertIsNone(reader.source_pdf_url(root, output))
            with patch("build_reader_site.os.path.relpath", side_effect=ValueError("different drives")):
                with self.assertRaisesRegex(ValueError, "relative path"):
                    reader.source_pdf_url(source, output)

    def test_generated_reader_hides_missing_link_and_preserves_online_home(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            text = root / "text"
            images = root / "images"
            text.mkdir()
            images.mkdir()
            (text / "chapters.json").write_text("[]")
            for name in ("images.json", "captions.json"):
                (images / name).write_text('{"pages": []}')
            source = root / "original.pdf"
            source.touch()
            output = root / "custom-reader"
            with patch.multiple(reader, ROOT=root, TEXT=text), \
                 patch.object(reader, "load_captions", return_value={}), \
                 patch.object(reader, "load_frontmatter", return_value=[]), \
                 patch.object(reader, "load_chapters", return_value=[]), \
                 patch.object(reader, "font_assets", return_value={}):
                for online, configured, hidden in ((False, None, True), (False, root / "missing.pdf", True),
                                                   (False, source, False), (True, source, False)):
                    reader.main(online=online, source_pdf=configured, output_dir=output)
                    index = (output / "index.html").read_text()
                    self.assertEqual('<a id="source-link" hidden' in index, hidden)
                    data = (output / "data.js").read_text()
                    self.assertNotIn(str(root), data)
                    if online:
                        self.assertIn('<a id="source-link" href="../">项目首页与下载</a>', index)
                        self.assertIn('"sourcePdf": null', data)
                    elif configured == source:
                        self.assertIn('"sourcePdf": "./../original.pdf"', data)
                    else:
                        self.assertIn('"sourcePdf": null', data)
                    self.assertIn('${book.sourcePdf}#page=${c.pdfPage}', (output / "app.js").read_text())


class ReviewManifestPathsTests(unittest.TestCase):
    def test_manifest_uses_names_and_hashes_preserves_master(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "master.pdf"
            target = root / "exports" / "review.pdf"
            with fitz.open() as document:
                page = document.new_page()
                page.insert_text((72, 72), "Portable review preserves text")
                document.set_toc([[1, "Chapter", 1]])
                document.save(source)
            original = source.read_bytes()
            build_review_one(source.resolve(), target.resolve())
            manifest_text = target.with_suffix(".review.json").read_text()
            manifest = json.loads(manifest_text)
            self.assertEqual((manifest["source"], manifest["target"]), (source.name, target.name))
            self.assertNotIn(str(root), manifest_text)
            self.assertEqual(manifest["source_sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(manifest["target_sha256"], hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(manifest["validation"]["text_fonts_positions_preserved"])
            with self.assertRaisesRegex(ValueError, "must not overwrite"):
                build_review_one(source, source)


if __name__ == "__main__":
    unittest.main()
