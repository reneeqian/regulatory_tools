from pathlib import Path
import json
import pytest
from regulatory_tools.evidence.evidence_report import generate_evidence_summary
from regulatory_tools.traceability.generator import build_trace_matrix

# ----------------------------
# Helpers
# ----------------------------

def create_dummy_requirements(path: Path):
    path.write_text(
        """
requirements:
  - id: VER-001
    description: Dummy requirement 1
  - id: VER-002
    description: Dummy requirement 2
  - id: VER-003
    description: Dummy requirement 3
"""
    )


def create_dummy_evidence(root: Path):
    """
    Creates a single evidence run directory using
    the CURRENT expected schema:
        {
            "test_id": "...",
            "requirements": ["VER-1"],
            "result": "PASS"
        }
    """
    run_dir = root / "20260101_120000"
    run_dir.mkdir(parents=True)

    record_1 = {
        "test_id": "test_something",
        "requirements": ["VER-001"],
        "result": "PASS",
    }

    record_2 = {
        "test_id": "test_other",
        "requirements": ["VER-002"],
        "result": "PASS",
    }

    (run_dir / "test_something.json").write_text(json.dumps(record_1))
    (run_dir / "test_other.json").write_text(json.dumps(record_2))

    return run_dir


# ----------------------------
# Tests
# ----------------------------
@pytest.mark.requirement("DOC-004")
@pytest.mark.requirement("INF-001")
@pytest.mark.requirement("INF-004")
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
    

@pytest.mark.requirement("INF-004")
def test_invalid_evidence_schema(tmp_path: Path):

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"

    evidence_root.mkdir()

    create_dummy_requirements(req_yaml)

    run = evidence_root / "run"
    run.mkdir()

    bad_record = {
        "requirements": ["VER-001"]
    }

    (run / "bad.json").write_text(json.dumps(bad_record))

    matrix = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    assert matrix


@pytest.mark.requirement("INF-001")
def test_latest_evidence_run_used(tmp_path: Path):

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence_runs"

    evidence_root.mkdir()

    create_dummy_requirements(req_yaml)

    create_dummy_evidence(evidence_root)

    newer = evidence_root / "20260102_120000"
    newer.mkdir()

    record = {
        "test_id": "test_new",
        "requirements": ["VER-001"],
        "result": "FAIL",
    }

    (newer / "fail.json").write_text(json.dumps(record))

    matrix = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    matrix_by_id = {row["requirement_id"]: row for row in matrix}

    assert matrix_by_id["VER-001"]["status"] == "FAIL"