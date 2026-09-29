"""JSON result serialization."""

from __future__ import annotations

import json
from pathlib import Path

from transit_audit.models import AuditResult


def write_results_json(result: AuditResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.model_dump(mode="json")
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
