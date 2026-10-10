"""Protect the user-approved R459 period without changing nearby punctuation."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import proofreading


class MissingPeriodTests(unittest.TestCase):
    def test_replay_adds_only_the_period_and_original_paragraph_break(self):
        rules = [rule for rule in proofreading.read_manifest()["patches"] if rule["id"] == "R459"]
        self.assertEqual({rule["variant"] for rule in rules}, {"simplified", "traditional"})
        self.assertEqual(len(rules), 2)
        for rule in rules:
            with self.subTest(variant=rule["variant"]), tempfile.TemporaryDirectory() as directory:
                text_root = Path(directory)
                target = text_root / rule["variant"] / rule["file"]
                target.parent.mkdir(parents=True)
                before, after = rule["before"], rule["after"]
                self.assertEqual(rule["pages"], [373])
                self.assertEqual(after.replace("。\n\n", ""), before)
                self.assertEqual(after.count("。\n\n"), 1)
                prefix = f"# Test\n\n<!-- PDF 372 -->\n{before}\n\n<!-- PDF 373 -->\n"
                suffix = f"\n\n<!-- PDF 375 -->\n她赶紧答道：OK,OK.\n\n原来\n{before}\n"
                target.write_text(prefix + before + suffix, encoding="utf-8")
                with patch.object(proofreading, "TEXT", text_root), \
                     patch.object(proofreading, "read_manifest", return_value={"patches": [rule]}), \
                     patch.object(proofreading, "rebuild_paginated_books"):
                    self.assertEqual(proofreading.apply_patches(), 1)
                    self.assertEqual(target.read_text(encoding="utf-8"), prefix + after + suffix)
                    self.assertEqual(proofreading.apply_patches(), 0)
                    self.assertEqual(target.read_text(encoding="utf-8"), prefix + after + suffix)

    def test_all_reading_sources_include_the_period_and_keep_r462(self):
        manifest = proofreading.read_manifest()
        for variant in ("simplified", "traditional"):
            rule = next(rule for rule in manifest["patches"] if rule["id"] == "R459" and rule["variant"] == variant)
            neighbor = next(rule for rule in manifest["patches"] if rule["id"] == "R462" and rule["variant"] == variant)
            expected_neighbor = "她赶紧答道：OK,OK.\n\n原来" if variant == "simplified" else "她趕緊答道：OK,OK.\n\n原來"
            self.assertEqual(neighbor["after"], expected_neighbor)
            for directory in (variant, f"{variant}-continuous"):
                for path in (proofreading.TEXT / directory / rule["file"], proofreading.TEXT / f"book-{directory}.md"):
                    with self.subTest(path=path):
                        text = path.read_text(encoding="utf-8")
                        self.assertEqual(text.count(rule["after"]), 1)
                        self.assertNotIn(rule["after"].replace("。\n\n", "\n\n"), text)
                        self.assertEqual(text.count(expected_neighbor), 1)

    def test_original_omission_remains_documented_with_its_reading_correction(self):
        manifest = proofreading.read_manifest()
        decision = next(entry for entry in manifest["dispositions"] if entry["id"] == "R459")
        self.assertEqual(decision["verification_status"], "original_book_issue")
        self.assertIn("按用户裁决", decision["final_action"])
        self.assertIn("漏印句号", decision["final_action"])
        qa = proofreading.BOOK / "qa"
        notes = (qa / "原文疑点说明.md").read_text(encoding="utf-8")
        entry = next(line for line in notes.splitlines() if "R459" in line)
        self.assertIn("原书漏句号，阅读版已补", entry)
        self.assertIn("第373页", entry)
        self.assertIn("「声音。」", entry)
        self.assertNotIn("R462", entry)
        changes = (qa / "本次修改说明.md").read_text(encoding="utf-8")
        self.assertIn("第373页（R459）", changes)


if __name__ == "__main__":
    unittest.main()
