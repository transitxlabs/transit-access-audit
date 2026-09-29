from pathlib import Path

import pytest

from transit_audit.gtfs.reader import parse_hhmmss, read_gtfs_zip, seconds_to_hhmmss

FIXTURES = Path(__file__).parent / "fixtures"


def test_read_minimal_valid_feed() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    assert not feed.table("stops").empty
    assert len(feed.table("stops")) == 6


def test_parse_hhmmss_past_midnight() -> None:
    assert parse_hhmmss("25:30:00") == 25 * 3600 + 30 * 60
    assert seconds_to_hhmmss(parse_hhmmss("25:30:00")) == "25:30:00"


def test_invalid_zip_raises() -> None:
    bad = FIXTURES / "not_a_zip.txt"
    bad.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="Not a valid ZIP"):
        read_gtfs_zip(bad)
