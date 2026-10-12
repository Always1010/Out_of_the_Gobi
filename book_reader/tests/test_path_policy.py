"""Portable path policy tests; local-path fixtures are assembled at runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_paths import check_repository, metadata_errors, text_errors


def unix_path(root="home"):
    return "/" + root + "/sample/book.pdf"


def windows_path():
    return "C:" + chr(92) + "Users" + chr(92) + "sample" + chr(92) + "book.pdf"


class PathPolicyTests(unittest.TestCase):
    def test_local_literals_in_code_docs_and_archives(self):
        paths = [unix_path(), unix_path("workspace"), unix_path("usr"),
                 windows_path(), "D:" + "/" + "books/book.pdf",
                 chr(92) * 2 + "server" + chr(92) + "share" + chr(92) + "book.pdf",
                 "file:" + "/" * 3 + "sample/book.pdf"]
        for name in ["tool.py", "README.md", "archive/old.txt", "workflow.yml"]:
            for path in paths:
                with self.subTest(name=name, path=path):
                    self.assertTrue(text_errors(f'input = "{path}"', name))

    def test_urls_xml_prose_and_runtime_paths_are_allowed(self):
        text = '\n'.join([
            'https://example.org' + unix_path("usr"),
            '<root xmlns="http://www.w3.org/2000/svg"/>',
            'Path(__file__).resolve().parents[1] / "images"',
            'FONT_DIR: ${{ runner.temp }}/gobi-fonts',
            'source = Path(args.source).resolve()',
            'font = Path(os.environ["GOBI_FONT_SC"])',
            '甲／乙；甲/乙；source/target; /api/books',
        ])
        self.assertEqual(text_errors(text, "example.txt"), [])

    def test_gitignore_root_patterns_only(self):
        pattern = "/" + "tmp/"
        self.assertEqual(text_errors(pattern + '\n!' + pattern, ".gitignore"), [])
        self.assertTrue(text_errors(pattern, "README.md"))
        self.assertTrue(text_errors(windows_path(), ".gitignore"))

    def test_metadata_recurses_and_catches_arbitrary_roots(self):
        for path in [unix_path("custom-storage"), windows_path(),
                     chr(92) + "relative-to-current-drive", "C:" + "drive-relative"]:
            with self.subTest(path=path):
                self.assertTrue(metadata_errors({"pages": [{"input_path": path}]}))
                self.assertTrue(metadata_errors({"source": path, "target": path}))
                self.assertTrue(metadata_errors({"files": [path]}))
                self.assertTrue(metadata_errors({"source_pdf": path, "target_pdf": path}))
        self.assertEqual(metadata_errors({"source": "book_reader/input/book.pdf",
                                          "target": "book.pdf", "input_path": None}), [])
        self.assertEqual(metadata_errors({"source": "https://example.org/book.pdf"}), [])
        self.assertEqual(metadata_errors({"text": "/literary/slash"}), [])

    def test_python_explicit_filesystem_contexts(self):
        path = unix_path("unfamiliar-root")
        for source in [f"source_pdf = {path!r}", f"source: str = {path!r}",
                       f"Path({path!r})", f"pathlib.Path({path!r})", f"open({path!r})"]:
            self.assertTrue(text_errors(source, "script.py"))
        self.assertEqual(text_errors('route = "/api/books"', "script.py"), [])
        self.assertEqual(text_errors('Path(args.source).resolve()', "script.py"), [])

    def test_escaped_json_is_checked_after_decoding(self):
        self.assertTrue(text_errors(json.dumps({"input_path": windows_path()}), "page.json"))
        self.assertTrue(text_errors(json.dumps({"source": unix_path("unknown")}), "review.json"))
        self.assertTrue(text_errors('{"source":', "broken.json"))

    def test_git_tracked_scope_and_optional_generated_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "archive").mkdir()
            (root / "archive" / "old.txt").write_text(unix_path(), encoding="utf-8")
            (root / "ignored.txt").write_text(windows_path(), encoding="utf-8")
            (root / "binary.bin").write_bytes(b"\x00" + unix_path().encode())
            subprocess.run(["git", "add", "archive/old.txt", "binary.bin"], cwd=root, check=True)
            count, errors = check_repository(root)
            self.assertEqual(count, 1)
            self.assertEqual(len(errors), 1)
            self.assertIn("archive/old.txt", errors[0])
            (root / "archive" / "old.txt").write_text("relative/book.pdf", encoding="utf-8")
            generated = root / "generated"
            generated.mkdir()
            manifest = generated / "review.json"
            manifest.write_text(json.dumps({"source": unix_path("unusual")}), encoding="utf-8")
            self.assertEqual(check_repository(root)[1], [])
            self.assertTrue(check_repository(root, [generated])[1])
            manifest.write_text(json.dumps({"source": "book.pdf"}), encoding="utf-8")
            self.assertEqual(check_repository(root, [manifest])[1], [])
            self.assertTrue(check_repository(root, [root / "missing.json"])[1])

    def test_encoded_archived_text_is_not_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            for name, encoding in [("utf16.txt", "utf-16"), ("legacy.txt", "latin-1")]:
                (root / name).write_bytes(("café " + unix_path()).encode(encoding))
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            count, errors = check_repository(root)
            self.assertEqual(count, 2)
            self.assertEqual(len(errors), 2)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_relative_symlinks_allowed_absolute_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "relative").symlink_to("book.pdf")
            (root / "absolute").symlink_to(unix_path())
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            errors = check_repository(root)[1]
            self.assertEqual(len(errors), 1)
            self.assertIn("absolute", errors[0])

    def test_checker_and_tests_do_not_embed_local_path_literals(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        for path in [scripts / "validate_paths.py", Path(__file__)]:
            self.assertEqual(text_errors(path.read_text(encoding="utf-8"), path.name), [])


if __name__ == "__main__":
    unittest.main()
