"""Publish four verified ebooks to an existing tag; never delete assets or tags."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

NAMES = tuple(f"走出戈壁-{script}.{extension}" for script in ("简体", "繁体") for extension in ("epub", "pdf"))
ASSET_NAMES = {
    f"走出戈壁-{script}.{extension}": f"out-of-the-gobi-{locale}.{extension}"
    for script, locale in (("简体", "zh-Hans"), ("繁体", "zh-Hant"))
    for extension in ("epub", "pdf")
}
MARKER = re.compile(r"<!-- gobi-ebooks (\{.*?\}) -->")


class GitHub:
    def __init__(self, repository: str, token: str):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid repository")
        self.repository, self.token = repository, token

    def request(self, method: str, path: str, data=None, *, upload=False):
        host = "uploads.github.com" if upload else "api.github.com"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "gobi-ebook-release"}
        if isinstance(data, bytes):
            headers["Content-Type"] = "application/octet-stream"
        elif data is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        request = Request(f"https://{host}/repos/{self.repository}/{path}", data=data, headers=headers, method=method)
        # Never blindly retry a write whose result is uncertain. A workflow rerun
        # inspects the draft and its assets before resuming missing uploads.
        with urlopen(request, timeout=180) as response:
            return json.load(response)

    def tag_sha(self, tag: str) -> str:
        obj = self.request("GET", f"git/ref/tags/{quote(tag, safe='')}")["object"]
        for _ in range(10):
            if obj["type"] == "commit":
                return obj["sha"]
            if obj["type"] != "tag":
                break
            obj = self.request("GET", f"git/tags/{obj['sha']}")["object"]
        raise ValueError("Tag does not resolve to a commit")

    def release(self, tag: str):
        try:
            return self.request("GET", f"releases/tags/{quote(tag, safe='')}")
        except HTTPError as error:
            if error.code != 404:
                raise
            # List explicitly to include drafts when resuming a partial upload.
            for page in range(1, 1001):
                releases = self.request("GET", f"releases?per_page=100&page={page}")
                match = next((item for item in releases if item["tag_name"] == tag), None)
                if match:
                    return match
                if len(releases) < 100:
                    return None
            raise RuntimeError("Too many releases; refusing an incomplete lookup")

    def assets(self, release_id: int):
        result = []
        for page in range(1, 1001):
            items = self.request("GET", f"releases/{release_id}/assets?per_page=100&page={page}")
            result.extend(items)
            if len(items) < 100:
                return result
        raise RuntimeError("Too many assets; refusing an incomplete lookup")


def checked_files(directory: Path) -> dict[str, str]:
    checksums = {}
    for line in (directory / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match or match[2] in checksums:
            raise ValueError("Invalid or duplicate checksum entry")
        checksums[match[2]] = match[1]
    if set(checksums) != set(NAMES):
        raise ValueError("The checksum list must contain exactly the four ebooks")
    for name in NAMES:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing or invalid ebook: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != checksums[name]:
            raise ValueError(f"Checksum mismatch: {name}")
    return checksums


def check_asset(asset, expected: str):
    if asset.get("state") != "uploaded" or asset.get("size", 0) <= 0 or asset.get("digest") != f"sha256:{expected}":
        raise ValueError(f"Existing/uploaded asset could not be verified: {asset.get('name')}; no asset was overwritten")


def publish(client: GitHub, tag: str, source_sha: str, directory: Path) -> str:
    if not re.fullmatch(r"book-v[0-9][0-9A-Za-z._-]*", tag):
        raise ValueError("Use an existing book-v version tag, for example book-v1.0")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("Invalid source commit SHA")
    hashes = checked_files(directory)

    def verify_tag():
        if client.tag_sha(tag) != source_sha:
            raise ValueError("Tag moved or does not match the commit that produced these ebooks")

    verify_tag()  # Also fails if the tag is absent; there is no tag-creation API.
    release = client.release(tag)
    assets = client.assets(release["id"]) if release else []
    body = (release.get("body") or "") if release else (
        f"四份校订电子书分别提供 EPUB／PDF 下载。\n\n"
        f"构建源提交：[{source_sha}](https://github.com/{client.repository}/commit/{source_sha})。\n\n"
        "保留原书已核对内容；尚不代表全书完成逐字人工校勘。\n"
    )
    matches = list(MARKER.finditer(body))
    if len(matches) > 1:
        raise ValueError("Ambiguous release metadata")
    metadata = json.loads(matches[0][1]) if matches else {"source_sha": source_sha, "assets": {}}
    if metadata.get("source_sha") != source_sha:
        raise ValueError("Existing release records a different source commit")
    recorded = metadata.get("assets", {})
    source_names = {remote: local for local, remote in ASSET_NAMES.items()}
    existing, unrelated = {}, []
    for asset in assets:
        name = source_names.get(asset["name"])
        if name is None and release and release["draft"] and matches:
            # GitHub stripped an earlier Chinese filename to '-.epub'. Adopt
            # only a unique, fully uploaded asset whose digest is in our own
            # same-source draft manifest; unknown files are never renamed.
            if asset["name"] in NAMES:
                candidates = [asset["name"]]
            elif asset["name"] in {"-.epub", "-.pdf"}:
                candidates = [n for n in NAMES if n.endswith(Path(asset["name"]).suffix)
                              and asset.get("digest") == f"sha256:{recorded.get(n)}"]
            else:
                candidates = []
            if len(candidates) == 1:
                name = candidates[0]
        if name is None:
            unrelated.append(asset)
            continue
        if name in existing:
            raise ValueError("Duplicate ebook asset names or digests")
        if name not in recorded:
            raise ValueError(f"Unrecognized existing ebook asset: {name}; no overwrite is allowed")
        check_asset(asset, recorded[name])
        existing[name] = asset
    if release and release["draft"] and (not matches or unrelated):
        raise ValueError("Refusing to publish an unrelated draft or its unrelated assets")
    if release and release.get("immutable"):
        if set(existing) != set(NAMES):
            raise ValueError("The existing Release is immutable and is missing ebooks; use a new version tag")
        verify_tag()
        print(f"Four verified ebook assets already exist: {release['html_url']}")
        return release["html_url"]
    # Keep verified uploads from earlier attempts; only missing files get the
    # new attempt's hashes (PDF/EPUB timestamps can change between rebuilds).
    metadata["assets"] = {name: recorded[name] if name in existing else hashes[name] for name in NAMES}
    marker = "<!-- gobi-ebooks " + json.dumps(metadata, ensure_ascii=False, sort_keys=True) + " -->"
    updated_body = MARKER.sub(lambda _: marker, body) if matches else body.rstrip() + "\n\n" + marker + "\n"
    verify_tag()
    if release is None:
        release = client.request("POST", "releases", {"tag_name": tag, "name": f"校订电子书 {tag}",
                                  "body": updated_body, "draft": True, "make_latest": "false"})
    elif updated_body != body:
        client.request("PATCH", f"releases/{release['id']}", {"body": updated_body})
    for name, asset in existing.items():
        if asset["name"] != ASSET_NAMES[name]:
            # Rename the verified failed upload in place. No delete, reupload,
            # replacement, or change of content is required to resume the draft.
            renamed = client.request("PATCH", f"releases/assets/{asset['id']}",
                                     {"name": ASSET_NAMES[name], "label": name})
            if renamed.get("name") != ASSET_NAMES[name]:
                raise ValueError("GitHub did not retain the safe ASCII asset name")
            check_asset(renamed, recorded[name])
    for name in NAMES:
        if name in existing:
            continue
        asset = client.request("POST", f"releases/{release['id']}/assets?" + urlencode({"name": ASSET_NAMES[name], "label": name}),
                               (directory / name).read_bytes(), upload=True)
        if asset.get("name") != ASSET_NAMES[name]:
            raise ValueError(f"GitHub changed the asset filename: {name}")
        check_asset(asset, hashes[name])
    final_assets = client.assets(release["id"])
    final = {asset["name"]: asset for asset in final_assets}
    for name in NAMES:
        check_asset(final[ASSET_NAMES[name]], metadata["assets"][name])
    verify_tag()
    # Publishing a draft is the final action, after all four assets are verified.
    if release["draft"]:
        if set(final) != set(ASSET_NAMES.values()):
            raise ValueError("Draft gained unrelated assets; refusing to publish them")
        release = client.request("PATCH", f"releases/{release['id']}", {"draft": False, "make_latest": "false"})
    url = release["html_url"]
    print(f"Published four separate ebook assets: {url}")
    return url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    client = GitHub(os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"])
    url = publish(client, args.tag, args.source_sha, args.directory)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(f"## 四份电子书已分别发布\n\n[打开 {args.tag} Release]({url})\n")


if __name__ == "__main__":
    main()
