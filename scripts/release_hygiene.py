"""Check tracked and prospective release text, including logs without a suffix filter."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PREFIXES = (".review/", "state/")
HOME_PATH_PATTERN = re.compile(r"/(?:Users|home|var/folders)/")
ATTRIBUTION_PATTERN = re.compile(r"(?i)^\s*(?:<!--\s*)?(?:co-authored-by:|assisted by)")


def is_release_path(name: str) -> bool:
    return bool(name) and not name.startswith(PRIVATE_PREFIXES)


def scan_release(root: Path = ROOT) -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root,
    )
    names = sorted(set(output.decode().split("\0")))
    offenders: list[str] = []
    for name in names:
        if not is_release_path(name):
            continue
        try:
            text = (root / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            # A test's regex declaration is source syntax, not an operational path.
            regex_declaration = name.startswith("tests/") and "re.compile(" in line
            if HOME_PATH_PATTERN.search(line) and not regex_declaration:
                offenders.append(f"{name}:{number}: absolute/home path")
            if "\u2014" in line:
                offenders.append(f"{name}:{number}: em dash")
            if ATTRIBUTION_PATTERN.search(line) and name != "scripts/release_hygiene.py":
                offenders.append(f"{name}:{number}: attribution line")
    return offenders


if __name__ == "__main__":
    violations = scan_release()
    print("\n".join(violations) if violations else "Release text scan: clean (including retained logs)")
    raise SystemExit(bool(violations))
