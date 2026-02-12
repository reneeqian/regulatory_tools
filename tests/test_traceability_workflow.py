import json
from pathlib import Path

import pytest

from regulatory_tools.traceability.generator import (
    generate_trace_rows,
    write_markdown,
)
from regulatory_tools.traceability.validate_traceability import (
    validate_traceability,
)


# ----------------------------
# Helpers
# ----------------------------

def create_dummy_requirements(path: Path):
    path.write_text(
        """
requirements:
  - id: CAC-REQ-001
    description: Dummy requirement 1
  - id: CAC-REQ-002
    description: Dummy requirement 2
  - id: CAC-REQ-003
    description: Dummy requirement 3
"""
    )


def create_dummy_test_file(path: Path):
    path.write_text(
        '''
def requirement(req_id):
    pass

def test_something():
    requirement("CAC-REQ-001")
    assert True

def test_other():
    requirement("CAC-REQ-002")
    assert True
'''
    )


def create_dummy_evidence(root: Path):
    run_dir = root / "20260101_120000"
    run_dir.mkdir(parents=True)

    record_1 = {
        "test_id": "test_something",
        "requirement_id": "CAC-REQ-001",
        "result": "PASS",
    }

    record_2 = {
        "test_id": "test_other",
        "requirement_id": "CAC-REQ-002",
        "result": "PASS",
    }

    (run_dir / "test_something.json").write_text(json.dumps(record_1))
    (run_dir / "test_other.json").write_text(json.dumps(record_2))

    return run_dir


# ----------------------------
# Tests
# ----------------------------

def test_full_traceability_workflow(tmp_path: Path):
    """
    End-to-end test:
      - requirements.yaml
      - test files with requirement markers
      - dummy evidence JSON
      - trace matrix generation
      - missing requirement detection
    """

    # --- Setup paths
    requirements_yaml = tmp_path / "requirements.yaml"
    tests_dir = tmp_path / "tests"
    evidence_root = tmp_path / "evidence_runs"
    output_md = tmp_path / "traceability.md"

    tests_dir.mkdir()
    evidence_root.mkdir()

    # --- Create inputs
    create_dummy_requirements(requirements_yaml)
    create_dummy_test_file(tests_dir / "test_dummy.py")
    create_dummy_evidence(evidence_root)

    # --- Validate requirement coverage
    missing, untracked = validate_traceability(
        requirements_yaml=requirements_yaml,
        test_dir=tests_dir,
    )

    # CAC-REQ-003 is declared but not tested
    assert "CAC-REQ-003" in missing

    # No extra undeclared requirements referenced
    assert not untracked

    # --- Generate trace rows from evidence
    rows = generate_trace_rows(evidence_root)

    assert len(rows) == 2
    assert {r.requirement_id for r in rows} == {
        "CAC-REQ-001",
        "CAC-REQ-002",
    }

    # --- Write markdown
    write_markdown(rows, output_md)

    assert output_md.exists()

    contents = output_md.read_text()

    assert "CAC-REQ-001" in contents
    assert "CAC-REQ-002" in contents
    assert "PASS" in contents
