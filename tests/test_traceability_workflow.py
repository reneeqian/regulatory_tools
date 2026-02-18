import json
from pathlib import Path

from regulatory_tools.traceability.generator import (
    build_trace_matrix,
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
    """
    Creates a single evidence run directory using
    the CURRENT expected schema:
        {
            "test_id": "...",
            "requirements": ["REQ-1"],
            "result": "PASS"
        }
    """
    run_dir = root / "20260101_120000"
    run_dir.mkdir(parents=True)

    record_1 = {
        "test_id": "test_something",
        "requirements": ["CAC-REQ-001"],
        "result": "PASS",
    }

    record_2 = {
        "test_id": "test_other",
        "requirements": ["CAC-REQ-002"],
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
    End-to-end validation of:

      - requirements.yaml parsing
      - requirement coverage validation
      - evidence ingestion
      - trace matrix construction
      - markdown generation
      - UNTESTED detection
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

    # --- Validate requirement coverage (static test scan)
    missing, untracked = validate_traceability(
        requirements_yaml=requirements_yaml,
        test_dir=tests_dir,
    )

    # CAC-REQ-003 declared but not referenced in tests
    assert "CAC-REQ-003" in missing

    # No undeclared requirements referenced
    assert not untracked

    # --- Build trace matrix (dynamic evidence-driven)
    matrix = build_trace_matrix(
        requirements_yaml=requirements_yaml,
        evidence_root=evidence_root,
    )

    assert len(matrix) == 3  # all declared requirements present

    # Convert to dict for easier validation
    matrix_by_id = {row["requirement_id"]: row for row in matrix}

    # Tested requirements
    assert matrix_by_id["CAC-REQ-001"]["status"] == "PASS"
    assert matrix_by_id["CAC-REQ-002"]["status"] == "PASS"

    # Untested requirement
    assert matrix_by_id["CAC-REQ-003"]["status"] == "UNTESTED"

    # Ensure linked tests recorded
    assert "test_something" in matrix_by_id["CAC-REQ-001"]["tests"]
    assert "test_other" in matrix_by_id["CAC-REQ-002"]["tests"]

    # --- Write markdown output
    write_markdown(matrix, output_md)

    assert output_md.exists()

    contents = output_md.read_text()

    # Matrix structure
    assert "Requirements Traceability Matrix" in contents
    assert "CAC-REQ-001" in contents
    assert "CAC-REQ-002" in contents
    assert "CAC-REQ-003" in contents

    # Status values
    assert "PASS" in contents
    assert "UNTESTED" in contents

    # Summary section
    assert "Total Requirements: 3" in contents
    assert "Tested: 2" in contents
    assert "Failures: 0" in contents
