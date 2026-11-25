"""Build the landscape TapTap H5 playtest ZIP with Python 3 (standard library)."""

import hashlib
import json
import tempfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "huhuhero-taptap.zip"


class EntryAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        url = attrs.get("href") if tag == "link" else attrs.get("src")
        if not url:
            return
        parts = urlsplit(url)
        name = unquote(parts.path)
        path = PurePosixPath(name)
        if parts.scheme or parts.netloc or path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Entry asset needs a local relative path: {url}")
        self.paths.add(path.as_posix())


def collect_files():
    entry = EntryAssets()
    entry.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    entry.close()
    files = {"index.html", "assets/atlas.json"} | entry.paths

    # The exported game loads its WebP sprites by name at runtime. Its sky
    # background is the one texture that has no dimensions entry in the atlas.
    atlas = json.loads((ROOT / "assets/atlas.json").read_text(encoding="utf-8"))
    files.update(f"assets/{key}.webp" for key in {*atlas, "bg_sky"})
    if not any(PurePosixPath(name).match("assets/index-*.js") for name in entry.paths):
        raise ValueError("Missing game bundle reference in index.html")
    for name in files:
        path = ROOT / name
        if ROOT not in path.resolve().parents or not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing, external or empty game file: {name}")
    return sorted(files)


def build():
    files = collect_files()
    OUTPUT.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUTPUT.parent) as staging:
        candidate = Path(staging) / OUTPUT.name
        with ZipFile(candidate, "w") as package:
            for name in files:
                # Fixed timestamps, order and permissions make repeat builds reproducible.
                info = ZipInfo(f"huhuhero/{name}", (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                package.writestr(info, (ROOT / name).read_bytes(), ZIP_DEFLATED, 9)

        with ZipFile(candidate) as package:
            if package.testzip() or package.namelist() != [f"huhuhero/{name}" for name in files]:
                raise ValueError("ZIP verification failed")
        candidate.replace(OUTPUT)
    print(f"{OUTPUT} ({len(files)} files, {OUTPUT.stat().st_size} bytes)")
    print(f"SHA-256 {hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    build()
