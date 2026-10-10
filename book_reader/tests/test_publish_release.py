"""Offline tests: no credentials, network calls, tags, or releases are created."""
import copy
import hashlib
import re
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_release import ASSET_NAMES, GitHub, NAMES, publish

SHA = "a" * 40
TAG = "book-v1.0"


class FakeGitHub:
    repository = "example/book"

    def __init__(self):
        self.item = None
        self.items = []
        self.writes = []
        self.fail_upload = None
        self.tag_checks = 0
        self.move_at = None

    def tag_sha(self, tag):
        self.tag_checks += 1
        return "b" * 40 if self.move_at == self.tag_checks else SHA

    def release(self, tag):
        return copy.deepcopy(self.item)

    def assets(self, release_id):
        return copy.deepcopy(self.items)

    def request(self, method, path, data, *, upload=False):
        self.writes.append((method, path, copy.deepcopy(data)))
        if method == "POST" and path == "releases":
            self.item = dict(data, id=1, html_url=f"https://github.com/{self.repository}/releases/tag/{TAG}")
            return copy.deepcopy(self.item)
        if method == "PATCH" and path.startswith("releases/assets/"):
            asset_id = int(path.rsplit("/", 1)[1])
            item = next(a for a in self.items if a["id"] == asset_id)
            item.update(data)
            return copy.deepcopy(item)
        if method == "PATCH":
            self.item.update(data)
            return copy.deepcopy(self.item)
        if upload:
            query = parse_qs(path.split("?", 1)[1])
            # Reproduce the real GitHub filename sanitization that exposed the bug.
            name = re.sub(r"[^A-Za-z0-9._-]", "", query["name"][0])
            if name == self.fail_upload:
                self.fail_upload = None
                raise RuntimeError("simulated interrupted upload")
            item = {"id": 100 + len(self.items), "name": name, "label": query.get("label", [""])[0], "state": "uploaded", "size": len(data), "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
            self.items.append(item)
            return copy.deepcopy(item)
        raise AssertionError((method, path))


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.client = FakeGitHub()
        self.make_files()

    def make_files(self, suffix=""):
        rows = []
        for name in NAMES:
            content = (name + suffix).encode()
            (self.directory / name).write_bytes(content)
            rows.append(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
        (self.directory / "SHA256SUMS.txt").write_text("".join(rows), encoding="utf-8")

    def run_publish(self, tag=TAG, sha=SHA):
        return publish(self.client, tag, sha, self.directory)

    def test_new_release_is_draft_until_exactly_four_files_are_verified(self):
        self.run_publish()
        self.assertFalse(self.client.item["draft"])
        self.assertEqual({x["name"] for x in self.client.items}, set(ASSET_NAMES.values()))
        self.assertTrue(self.client.writes[0][2]["draft"])
        self.assertEqual(self.client.writes[-1][2], {"draft": False, "make_latest": "false"})
        self.assertNotIn("target_commitish", self.client.writes[0][2])

    def test_rerun_keeps_verified_existing_files_despite_new_timestamps(self):
        self.run_publish()
        previous = copy.deepcopy(self.client.items)
        self.make_files("new build timestamp")
        self.client.writes.clear()
        self.run_publish()
        self.assertEqual(self.client.writes, [])
        self.assertEqual(self.client.items, previous)

    def test_partial_draft_resumes_only_missing_files(self):
        self.client.fail_upload = ASSET_NAMES[NAMES[2]]
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            self.run_publish()
        self.assertTrue(self.client.item["draft"])
        old = copy.deepcopy(self.client.items)
        self.make_files("rerun")
        self.run_publish()
        self.assertFalse(self.client.item["draft"])
        self.assertEqual(self.client.items[:2], old)
        self.assertEqual(len(self.client.items), 4)

    def test_existing_published_release_keeps_unrelated_asset_and_notes(self):
        self.client.item = {"id": 1, "tag_name": TAG, "draft": False, "body": "Existing user notes", "html_url": "https://example.org/release"}
        other = {"name": "unrelated.txt", "size": 9}
        self.client.items = [other.copy()]
        self.run_publish()
        self.assertEqual(self.client.items[0], other)
        self.assertTrue(self.client.item["body"].startswith("Existing user notes\n"))
        self.assertEqual(len(self.client.items), 5)
        self.assertFalse(any(method == "DELETE" for method, _, _ in self.client.writes))

    def test_unknown_same_name_asset_is_never_overwritten(self):
        self.client.item = {"id": 1, "tag_name": TAG, "draft": False, "body": ""}
        self.client.items = [{"name": ASSET_NAMES[NAMES[0]], "size": 9}]
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            self.run_publish()
        self.assertEqual(self.client.writes, [])

    def test_unrelated_draft_is_not_published(self):
        self.client.item = {"id": 1, "tag_name": TAG, "draft": True, "body": "User draft"}
        with self.assertRaisesRegex(ValueError, "unrelated draft"):
            self.run_publish()
        self.assertEqual(self.client.writes, [])

    def test_wrong_tag_commit_fails_before_writing(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.run_publish(sha="b" * 40)
        self.assertEqual(self.client.writes, [])

    def test_moved_tag_blocks_final_draft_publication(self):
        self.client.move_at = 3
        with self.assertRaisesRegex(ValueError, "Tag moved"):
            self.run_publish()
        self.assertTrue(self.client.item["draft"])

    def test_malformed_tag_cannot_inject_shell_or_api_path(self):
        for tag in ("main", "book-v1/../../main", "book-v1\nother", "book-v1;echo bad"):
            with self.assertRaises(ValueError):
                self.run_publish(tag=tag)
        self.assertEqual(self.client.writes, [])

    def test_modified_file_blocks_all_writes(self):
        (self.directory / NAMES[0]).write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            self.run_publish()
        self.assertEqual(self.client.writes, [])

    def test_missing_file_blocks_all_writes(self):
        (self.directory / NAMES[0]).unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.run_publish()
        self.assertEqual(self.client.writes, [])

    def test_wrong_existing_digest_blocks_all_writes(self):
        self.run_publish()
        self.client.items[0]["digest"] = "sha256:" + "f" * 64
        self.client.writes.clear()
        with self.assertRaisesRegex(ValueError, "could not be verified"):
            self.run_publish()
        self.assertEqual(self.client.writes, [])

    def test_draft_with_new_unrelated_asset_stays_private(self):
        self.client.fail_upload = ASSET_NAMES[NAMES[1]]
        with self.assertRaises(RuntimeError):
            self.run_publish()
        self.client.items.append({"name": "private-notes.txt", "size": 10})
        self.client.writes.clear()
        with self.assertRaisesRegex(ValueError, "unrelated"):
            self.run_publish()
        self.assertTrue(self.client.item["draft"])
        self.assertEqual(self.client.writes, [])

    def test_immutable_release_with_missing_files_stops_before_writing(self):
        self.client.item = {"id": 1, "tag_name": TAG, "draft": False, "immutable": True, "body": "Existing notes"}
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.run_publish()
        self.assertEqual(self.client.writes, [])

    def test_complete_immutable_release_is_a_no_op(self):
        self.run_publish()
        self.client.item["immutable"] = True
        self.client.writes.clear()
        self.make_files("rerun")
        self.run_publish()
        self.assertEqual(self.client.writes, [])

    def test_zero_byte_starter_asset_stops_without_deleting_it(self):
        self.client.fail_upload = ASSET_NAMES[NAMES[1]]
        with self.assertRaises(RuntimeError):
            self.run_publish()
        self.client.items.append({"name": ASSET_NAMES[NAMES[1]], "size": 0, "state": "starter", "digest": None})
        self.client.writes.clear()
        with self.assertRaisesRegex(ValueError, "could not be verified"):
            self.run_publish()
        self.assertEqual(self.client.writes, [])
        self.assertTrue(self.client.item["draft"])

    def test_uploaded_names_are_ascii_with_distinct_script_labels(self):
        self.run_publish()
        self.assertEqual({a["name"] for a in self.client.items}, set(ASSET_NAMES.values()))
        self.assertEqual({a["label"] for a in self.client.items}, set(NAMES))
        self.assertTrue(all(a["name"].isascii() for a in self.client.items))

    def broken_old_draft(self):
        self.run_publish()
        self.client.item["draft"] = True
        self.client.items = [self.client.items[0]]
        self.client.items[0]["name"] = "-.epub"
        self.client.items[0]["label"] = ""
        self.client.writes.clear()

    def test_known_sanitized_upload_is_renamed_in_place_and_resumed(self):
        self.broken_old_draft()
        asset_id = self.client.items[0]["id"]
        digest = self.client.items[0]["digest"]
        self.make_files("new attempt")
        self.run_publish()
        self.assertEqual(self.client.items[0]["id"], asset_id)
        self.assertEqual(self.client.items[0]["digest"], digest)
        self.assertEqual(self.client.items[0]["name"], ASSET_NAMES[NAMES[0]])
        self.assertEqual(len(self.client.items), 4)
        self.assertFalse(self.client.item["draft"])
        self.assertFalse(any(method == "DELETE" for method, _, _ in self.client.writes))

    def test_unknown_sanitized_asset_is_not_adopted(self):
        self.broken_old_draft()
        self.client.items[0]["digest"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(ValueError, "unrelated"):
            self.run_publish()
        self.assertEqual(self.client.writes, [])

    def test_retagged_source_cannot_reuse_old_draft_assets(self):
        self.broken_old_draft()
        self.client.tag_sha = lambda _: "b" * 40
        with self.assertRaisesRegex(ValueError, "different source"):
            self.run_publish(sha="b" * 40)
        self.assertEqual(self.client.writes, [])

    def test_annotated_tag_is_peeled_to_commit(self):
        client = GitHub("example/book", "unused")
        objects = iter([{"object": {"type": "tag", "sha": "c" * 40}}, {"object": {"type": "commit", "sha": SHA}}])
        client.request = lambda *_: next(objects)
        self.assertEqual(client.tag_sha(TAG), SHA)


if __name__ == "__main__":
    unittest.main()
