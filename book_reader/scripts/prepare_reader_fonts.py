"""Download verified reader font sources into a build cache; never install fonts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

NOTO = "https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c"
SOURCES = {
    "NotoSansSC-VF.ttf": (
        f"{NOTO}/Sans/Variable/TTF/NotoSansCJKsc-VF.ttf",
        "990c807e79c25662a5a9ecf7f971baeb2bf2eab9a559e5ecf15cdfdb8561d21f",
    ),
    "NotoSerifSC-VF.ttf": (
        f"{NOTO}/Serif/Variable/TTF/NotoSerifCJKsc-VF.ttf",
        "dbf8ac0523dc19fa6294c52ce127a81c1b5b43ddc2e0915942bfd50aa58f4c53",
    ),
    "LXGWWenKai-Light.ttf": (
        "https://github.com/lxgw/LxgwWenKai/releases/download/v1.522/LXGWWenKai-Light.ttf",
        "526ec70cbb0118e871d481f8179e03ff045f0e4d72d080dcca87950c4ab27cca",
    ),
}


def checksum(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def prepare(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, (url, digest) in SOURCES.items():
        destination = directory / name
        if not destination.is_file() or checksum(destination) != digest:
            temporary = destination.with_suffix(".download")
            print(f"Downloading {name}", flush=True)
            try:
                with urlopen(url, timeout=120) as response, temporary.open("wb") as target:
                    while chunk := response.read(1024 * 1024):
                        target.write(chunk)
                if checksum(temporary) != digest:
                    raise ValueError(f"Font checksum mismatch: {name}")
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        print(f"Verified {name}", flush=True)
    for family in ("Sans", "Serif"):
        with TTFont(directory / f"Noto{family}SC-VF.ttf", recalcTimestamp=False) as font:
            instantiateVariableFont(font, {"wght": 400}, inplace=True)
            font.save(directory / f"Noto{family}SC-Regular.ttf")
    print(f"Prepared static reader fonts in {directory}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Build-cache directory for font files")
    prepare(parser.parse_args().directory)
