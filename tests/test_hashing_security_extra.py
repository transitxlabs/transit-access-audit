from pathlib import Path

from transit_audit.hashing import sha256_bytes, sha256_file
from transit_audit.security import is_safe_url, sanitize_identifier, validate_url


def test_hashing_helpers(tmp_path: Path) -> None:
    path = tmp_path / "x.txt"
    path.write_text("abc", encoding="utf-8")
    assert sha256_file(path) == sha256_bytes(b"abc")


def test_safe_url_and_sanitize() -> None:
    assert is_safe_url("https://example.com")
    assert not is_safe_url("data:text/plain,hi")
    assert sanitize_identifier("a/b c") == "a_b_c"


def test_validate_url_mailto() -> None:
    assert validate_url("mailto:test@example.com") == "mailto:test@example.com"
