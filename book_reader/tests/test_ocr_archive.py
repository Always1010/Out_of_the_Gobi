"""Archived scan utilities and disposable OCR exports stay portable."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

BOOK = Path(__file__).resolve().parents[1]
ARCHIVE = BOOK / "archive" / "scripts"
sys.path.insert(0, str(BOOK / "scripts"))
import ocr_common


def load_tool(name):
    spec = importlib.util.spec_from_file_location("archived_" + name, ARCHIVE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OCRArchiveTests(unittest.TestCase):
    def test_shared_helpers_read_retained_ocr(self):
        self.assertEqual(ocr_common.normalized(" 中：文。 "), "中文")
        self.assertEqual(ocr_common.chinese_number(21), "二十一")
        self.assertEqual(ocr_common.repair_star_break("1大X"), "★★★")
        self.assertEqual(ocr_common.reading_paragraphs(9, "full_page"), [])
        self.assertTrue(ocr_common.load_page(1)[0])

    def test_retained_evidence_has_only_logical_image_names(self):
        paths = sorted((BOOK / "ocr" / "paddle_small").glob("page-*.json"))
        self.assertEqual(len(paths), 420)
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["res"]["input_path"], path.stem + ".png")
        self.assertFalse((BOOK / "ocr" / "pages.json").exists())
        self.assertFalse((BOOK / "ocr" / "pages").exists())

    def test_export_only_from_other_working_directory_without_pdf(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "export"
            subprocess.run([sys.executable, str(ARCHIVE / "run_ocr.py"), "--export-only",
                            "--pdf", str(Path(temp) / "absent.pdf"), "--output", str(output)],
                           cwd=temp, check=True, capture_output=True)
            entries = json.loads((output / "pages.json").read_text())
            self.assertEqual(len(entries), 420)
            self.assertTrue(all(item["status"] == "complete" for item in entries))
            self.assertEqual(len(list((output / "pages").glob("*.txt"))), 420)
            lines = ocr_common.load_page(1)[0]
            self.assertEqual((output / "pages/page-001.txt").read_text(), "\n".join(lines).strip() + "\n")

    def test_scan_help_and_pdf_override(self):
        for name in ("run_ocr", "render_image_pages", "build_contact_sheets"):
            with tempfile.TemporaryDirectory() as temp:
                result = subprocess.run([sys.executable, str(ARCHIVE / (name + ".py")), "--help"],
                                        cwd=temp, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--pdf", result.stdout)
        self.assertEqual(load_tool("build_contact_sheets").OUTPUT, BOOK / "archive/contact_sheets")

    def test_ocr_honors_existing_cache_and_configurable_models_and_temp(self):
        tool = load_tool("run_ocr")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf = root / "scan.pdf"
            pdf.touch()
            payload = {"res": {"input_path": "/private/temp/page-001.png", "rec_texts": ["文字"], "rec_scores": [0.9]}}
            factory = Mock(return_value=SimpleNamespace(predict=lambda image: [SimpleNamespace(json=payload)]))
            def render(command, **kwargs):
                Path(command[-1]).with_suffix(".png").touch()
            env = {"GOBI_SOURCE_PDF": str(pdf), "PADDLE_PDX_CACHE_HOME": str(root / "paddle"),
                   "HF_HOME": str(root / "hf"), "GOBI_TEMP_DIR": str(root / "scratch"),
                   "GOBI_OCR_DET_MODEL_DIR": str(root / "det"), "GOBI_OCR_REC_MODEL_DIR": str(root / "rec")}
            argv = ["run_ocr.py", "--pages", "1", "--output", str(root / "export")]
            with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", argv), \
                 patch.dict(sys.modules, {"paddleocr": SimpleNamespace(PaddleOCR=factory)}), \
                 patch.object(tool, "OCR_DIR", root / "raw"), patch.object(tool, "PAGES", 1), \
                 patch.object(tool.subprocess, "run", side_effect=render):
                tool.main()
                self.assertEqual(os.environ["PADDLE_PDX_CACHE_HOME"], env["PADDLE_PDX_CACHE_HOME"])
                self.assertEqual(os.environ["HF_HOME"], env["HF_HOME"])
            self.assertEqual(factory.call_args.kwargs["text_detection_model_dir"], str(root / "det"))
            self.assertEqual(factory.call_args.kwargs["text_recognition_model_dir"], str(root / "rec"))
            self.assertTrue((root / "scratch").is_dir())
            self.assertEqual(list((root / "scratch").iterdir()), [])
            self.assertEqual(json.loads((root / "raw/page-001.json").read_text())["res"]["input_path"], "page-001.png")


if __name__ == "__main__":
    unittest.main()
