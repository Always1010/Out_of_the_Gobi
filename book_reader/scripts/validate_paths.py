"""Reject machine-local path literals in Git-tracked text and JSON metadata.

Paths computed at runtime from CLI options, environment variables, or the
repository location remain valid. Optional --manifest files/directories also
check generated (untracked) JSON before it is archived or published.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
import sys
import warnings

ROOT = Path(__file__).resolve().parents[2]
# Known filesystem roots distinguish paths from prose punctuation and web routes.
LOCAL_ROOTS = (
    "Users", "home", "root", "workspace", "workspaces", "tmp", "temp",
    "private", "var", "usr", "opt", "etc", "mnt", "media", "Volumes",
    "Library", "Applications", "System", "Windows", "Program Files", "srv",
    "data", "app", "code", "run", "proc", "sys", "dev", "bin", "sbin",
    "lib", "lib64", "snap", "nix", "storage", "content", "kaggle",
)
BOUNDARY = r"(?<![\w/\\$}])"
LOCAL_LITERAL = re.compile(
    BOUNDARY + r"(?:[A-Za-z]:[\\/][^\s\"'`<>]*"
    r"|\\{2,}[A-Za-z0-9_.-]+\\+[A-Za-z0-9_$.-]+"
    r"|/(?:" + "|".join(re.escape(root) for root in LOCAL_ROOTS)
    + r")(?=/|[\s\"'`),;]|$)(?:/[^\s\"'`<>]*)?"
    r"|file:" + r"/+[^\s\"'`<>]+)"
)
URL = re.compile(r"\b(?!file:)[A-Za-z][A-Za-z0-9+.-]*://[^\s\"'`<>]+")
PATH_KEYS = {
    "path", "paths", "source", "target", "input", "output", "file", "files",
    "filename", "directory", "image", "image_path", "input_path", "output_path",
    "source_path", "target_path", "source_pdf", "target_pdf",
    "input_file", "output_file", "input_dir", "output_dir",
}


def is_path_key(key: str) -> bool:
    return key.lower() in PATH_KEYS or key.lower().endswith(
        ("_path", "_paths", "_file", "_files", "_dir", "_directory")
    )


def metadata_errors(value, location: str = "$", path_field: bool = False) -> list[str]:
    """Validate persisted path fields, including unfamiliar Unix root names."""
    errors = []
    if isinstance(value, dict):
        for key, item in value.items():
            errors.extend(metadata_errors(item, f"{location}.{key}", is_path_key(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(metadata_errors(item, f"{location}[{index}]", path_field))
    elif path_field and isinstance(value, str):
        if URL.fullmatch(value):
            return []
        windows = PureWindowsPath(value)
        if (PurePosixPath(value).is_absolute() or windows.is_absolute()
                or windows.drive or windows.root or value.lower().startswith("file:")):
            errors.append(f"{location}: persisted path must be relative: {value!r}")
    return errors


def python_path_errors(text: str, name: str) -> list[str]:
    """Check explicit Python filesystem contexts without guessing at web routes."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text, filename=name)
    except SyntaxError:
        # Archived Python may target another interpreter. The text check still runs.
        return []
    errors = []
    for node in ast.walk(tree):
        values = []
        if isinstance(node, ast.Call) and node.args:
            function = node.func
            label = function.id if isinstance(function, ast.Name) else (
                function.attr if isinstance(function, ast.Attribute) else "")
            if label in {"Path", "PurePath", "PurePosixPath", "PureWindowsPath"} or (
                    isinstance(function, ast.Name) and label == "open"):
                values.append(node.args[0])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and is_path_key(target.id) for target in targets):
                values.append(node.value)
        for value in values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                errors.extend(f"{name}:{value.lineno}: {error}"
                              for error in metadata_errors({"path": value.value}))
    return errors


def text_errors(text: str, name: str) -> list[str]:
    errors = []
    for number, line in enumerate(text.splitlines(), 1):
        # A root-anchored ignore pattern refers to the repository, not the host.
        if Path(name).name == ".gitignore" and line.lstrip().startswith(("/", "!/")):
            continue
        masked = URL.sub(lambda match: " " * len(match.group()), line)
        for match in LOCAL_LITERAL.finditer(masked):
            errors.append(f"{name}:{number}: local filesystem literal {match.group()!r}")
    if name.lower().endswith(".py"):
        errors.extend(python_path_errors(text, name))
    if name.lower().endswith(".json"):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"{name}:{exc.lineno}: invalid JSON: {exc.msg}")
        else:
            errors.extend(f"{name}:{error}" for error in metadata_errors(value))
    return errors


def read_text(path: Path) -> str | None:
    data = path.read_bytes()
    # Recognize UTF-16/32 text too; binary files are not path-policy input.
    for signature, encoding in ((b"\xff\xfe\x00\x00", "utf-32"),
                                (b"\x00\x00\xfe\xff", "utf-32"),
                                (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if data.startswith(signature):
            return data.decode(encoding)
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Legacy archived text may have a non-UTF-8 encoding. Filesystem path
        # syntax is ASCII-compatible; preserve these bytes for the lexical check.
        return data.decode("latin-1")


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root,
                            check=True, stdout=subprocess.PIPE)
    return [root / name.decode("utf-8", errors="surrogateescape")
            for name in result.stdout.split(b"\x00") if name]


def check_repository(root: Path, manifests: list[Path] | None = None) -> tuple[int, list[str]]:
    errors = []
    count = 0
    for path in tracked_files(root):
        # Deletions in the current worktree will not be present in a fresh CI checkout.
        if path.is_symlink():
            target = os.readlink(path)
            errors.extend(f"{path.relative_to(root)}:{error}"
                          for error in metadata_errors({"target": target}))
            continue
        if not path.exists():
            continue
        text = read_text(path)
        if text is not None:
            count += 1
            errors.extend(text_errors(text, path.relative_to(root).as_posix()))
    for requested in manifests or []:
        paths = sorted(requested.rglob("*.json")) if requested.is_dir() else [requested]
        if not paths:
            errors.append(f"{requested}: no JSON manifests found")
        for path in paths:
            if not path.is_file():
                errors.append(f"{path}: manifest does not exist")
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
                value = json.loads(text)
            except (UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"{path}: invalid JSON manifest: {exc}")
                continue
            count += 1
            errors.extend(f"{path}:{error}" for error in metadata_errors(value))
            errors.extend(text_errors(text, str(path)))
    return count, list(dict.fromkeys(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Git working tree to check")
    parser.add_argument("--manifest", type=Path, action="append", default=[],
                        help="Also check a generated JSON file or directory (repeatable)")
    args = parser.parse_args()
    try:
        count, errors = check_repository(args.root.resolve(), args.manifest)
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        print(f"Path policy could not run: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Path policy passed: {count} text files/manifests checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
