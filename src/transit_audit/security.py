"""Security helpers for report generation."""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

_BLOCKED_SCHEMES = frozenset({"javascript", "data", "vbscript"})
_ALLOWED_SCHEMES = frozenset({"http", "https", "mailto"})


def escape_text(value: str | int | float | None) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def validate_url(url: str | None) -> str | None:
    if url is None or url == "":
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme == "" and url.startswith("//"):
        raise ValueError(f"Protocol-relative URLs are not allowed: {url}")
    if parsed.scheme.lower() in _BLOCKED_SCHEMES:
        raise ValueError(f"Blocked URL scheme: {parsed.scheme}")
    if parsed.scheme and parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    if parsed.scheme == "":
        raise ValueError(f"URL must include an explicit scheme: {url}")
    return url


def is_safe_url(url: str) -> bool:
    try:
        validate_url(url)
    except ValueError:
        return False
    return True


def sanitize_identifier(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", value)
