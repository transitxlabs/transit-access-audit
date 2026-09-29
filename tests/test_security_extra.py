import pytest

from transit_audit.security import validate_url


def test_validate_url_requires_scheme() -> None:
    with pytest.raises(ValueError, match="explicit scheme"):
        validate_url("example.com/page")
