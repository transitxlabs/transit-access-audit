from pathlib import Path

from transit_audit.models import Severity
from transit_audit.validator.mobilitydata import ingest_validator_report

FIXTURES = Path(__file__).parent / "fixtures"


def test_ingest_validator_report() -> None:
    findings, meta = ingest_validator_report(FIXTURES / "validator_broken_references_report.json")
    assert findings[0].check_id == "GTFS.MD.foreign_key_referential_integrity"
    assert findings[0].severity == Severity.ERROR
    assert meta["validator_name"] == "MobilityData GTFS Validator"
