#!/usr/bin/env python3
"""Download public GTFS feeds for local evaluation (not run in CI)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = ROOT / ".cache" / "gtfs"
FROZEN_MANIFESTS = ROOT / "docs" / "bounds_eval" / "frozen_feed_manifests.json"
MAX_COMPRESSED_BYTES = 500 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def _load_frozen_manifests() -> dict[str, dict[str, str | int]]:
    return json.loads(FROZEN_MANIFESTS.read_text(encoding="utf-8"))


FEEDS = {
    name: {
        "url": spec["url"],
        "filename": spec["filename"],
        "attribution": spec["attribution"],
        "licence_url": spec["licence_url"],
        "sha256": spec["sha256"],
        "bytes": spec["bytes"],
        "snapshot_path": spec.get("snapshot_path", ""),
    }
    for name, spec in _load_frozen_manifests().items()
}


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {url}")
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")


def _write_manifest(name: str, spec: dict[str, str | int], cache_dir: Path, digest: str, total: int) -> None:
    manifest = cache_dir / f"{name}_manifest.txt"
    text = (
        "\n".join(
            [
                f"feed={name}",
                f"url={spec['url']}",
                f"sha256={digest}",
                f"bytes={total}",
                f"licence_url={spec['licence_url']}",
                f"attribution={spec['attribution']}",
            ]
        )
        + "\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=cache_dir,
                                     prefix=f".{name}_manifest-", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, manifest)
    finally:
        temporary.unlink(missing_ok=True)


def fetch_feed(name: str, cache_dir: Path, *, force: bool = False) -> Path:
    if name not in FEEDS:
        raise ValueError(f"Unknown feed {name!r}; choices: {', '.join(sorted(FEEDS))}")
    spec = FEEDS[name]
    _validate_url(str(spec["url"]))
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / str(spec["filename"])
    expected = str(spec["sha256"])
    if destination.exists() and not force:
        hasher = hashlib.sha256()
        with destination.open("rb") as handle:
            for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
                hasher.update(chunk)
        if hasher.hexdigest() == expected and destination.stat().st_size == int(spec["bytes"]):
            _write_manifest(name, spec, cache_dir, expected, int(spec["bytes"]))
            return destination
    request = urllib.request.Request(
        str(spec["url"]),
        headers={"User-Agent": "transit-access-audit/0.3.0"},
    )
    hasher = hashlib.sha256()
    total = 0
    snapshot = ROOT / str(spec.get("snapshot_path", ""))
    source = (snapshot.open("rb") if not force and snapshot.is_file()
              else urllib.request.urlopen(request, timeout=600))
    temporary: Path | None = None
    try:
        with source as response, tempfile.NamedTemporaryFile(
            mode="wb", dir=cache_dir, prefix=f".{destination.name}-", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_COMPRESSED_BYTES:
                    raise ValueError(
                        f"Feed {name!r} exceeds {MAX_COMPRESSED_BYTES} byte compressed limit"
                    )
                hasher.update(chunk)
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        digest = hasher.hexdigest()
        if digest != expected:
            raise ValueError(
                f"Feed {name!r} SHA-256 mismatch: expected {expected}, observed {digest}. "
                "Use the content-addressed snapshot in frozen_feed_manifests.json."
            )
        if total != int(spec["bytes"]):
            raise ValueError(
                f"Feed {name!r} byte count mismatch: expected {spec['bytes']}, observed {total}."
            )
        os.replace(temporary, destination)
        _write_manifest(name, spec, cache_dir, digest, total)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feed", choices=sorted(FEEDS), help="Feed identifier")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE,
        help="Directory for downloaded feeds",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even when the cached snapshot matches the frozen manifest",
    )
    args = parser.parse_args()
    try:
        path = fetch_feed(args.feed, args.cache_dir, force=args.force)
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
