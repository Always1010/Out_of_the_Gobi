"""Page-scoped regression checks for the user-confirmed R142 comma."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import proofreading


class PoemCommaTests(unittest.TestCase):
    def test_replay_changes_only_the_confirmed_comma_and_keeps_verse_lines(self):
        manifest = proofreading.read_manifest()
        rules = [rule for rule in manifest["patches"] if rule["id"] == "R142"]
        self.assertEqual({rule["variant"] for rule in rules}, {"simplified", "traditional"})
        self.assertEqual(len(rules), 2)
        for rule in rules:
            with self.subTest(variant=rule["variant"]), tempfile.TemporaryDirectory() as directory:
                text_root = Path(directory)
                target = text_root / rule["variant"] / rule["file"]
                target.parent.mkdir(parents=True)
                verse = "曲折又漫長" if rule["variant"] == "traditional" else "曲折又漫长"
                before, after = rule["before"], rule["after"]
                self.assertEqual(rule["pages"], [136])
                self.assertEqual(before.count(verse + "·"), 1)
                self.assertEqual(after.count(verse + "，  \n"), 1)
                self.assertEqual(after.replace("  \n", ""), before.replace(verse + "·", verse + "，"))
                prefix = f"# Test\n\n<!-- PDF 135 -->\n{verse}·\n\n<!-- PDF 136 -->\n"
                suffix = "\n\n珍妮特·耶伦\n\n<!-- PDF 137 -->\n其他·原文\n"
                target.write_text(prefix + before + suffix, encoding="utf-8")
                with patch.object(proofreading, "TEXT", text_root), \
                     patch.object(proofreading, "read_manifest", return_value={"patches": [rule]}), \
                     patch.object(proofreading, "rebuild_paginated_books"):
                    self.assertEqual(proofreading.apply_patches(), 1)
                    self.assertEqual(target.read_text(encoding="utf-8"), prefix + after + suffix)
                    self.assertEqual(proofreading.apply_patches(), 0)
                    self.assertEqual(target.read_text(encoding="utf-8"), prefix + after + suffix)

    def test_decision_is_resolved_and_moved_to_modification_notes(self):
        manifest = proofreading.read_manifest()
        decision = next(entry for entry in manifest["dispositions"] if entry["id"] == "R142")
        self.assertEqual(decision["verification_status"], "confirmed_transcription_error")
        self.assertIn("按用户裁决", decision["final_action"])
        self.assertFalse(any(entry["id"] == "R142" for entry in manifest["preserved_text"]))
        qa = proofreading.BOOK / "qa"
        self.assertNotIn("R142", (qa / "原文疑点说明.md").read_text(encoding="utf-8"))
        notes = (qa / "本次修改说明.md").read_text(encoding="utf-8")
        self.assertIn("R142", notes)
        self.assertIn("「曲折又漫长，」", notes)


if __name__ == "__main__":
    unittest.main()
