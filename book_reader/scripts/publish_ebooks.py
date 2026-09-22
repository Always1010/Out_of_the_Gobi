"""Copy the four generated ebooks from ignored output/ to tracked project root."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "book_reader" / "output"
NAMES = tuple(
    f"走出戈壁-{script}.{extension}"
    for script in ("简体", "繁体")
    for extension in ("epub", "pdf")
)


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Only verify that tracked copies match generated files")
    args = parser.parse_args()
    missing = [name for name in NAMES if not (SOURCE / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Build the missing files first: {', '.join(missing)}")
    for name in NAMES:
        source = SOURCE / name
        target = ROOT / name
        if not args.check:
            shutil.copy2(source, target)
        if not target.is_file() or digest(source) != digest(target):
            raise RuntimeError(f"Published file differs from generated file: {name}")
        print(f"{'Verified' if args.check else 'Published'} {target}")


if __name__ == "__main__":
    main()
