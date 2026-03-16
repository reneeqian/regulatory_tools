from regulatory_tools.evidence.evidence_report import generate_evidence_summary
from pathlib import Path
import json


def test_evidence_summary(tmp_path):

    run = tmp_path / "run"
    run.mkdir()

    record = {
        "test_id": "test_example",
        "requirements": ["VER-001"],
        "result": "PASS",
    }

    (run / "rec.json").write_text(json.dumps(record))

    report = generate_evidence_summary(run)

    assert report["total_tests"] == 1