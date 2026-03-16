import json
from pathlib import Path
from importlib_resources import contents
import pytest

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
    assert "| PASS |" in contents
    assert "| UNTESTED |" in contents

    # Summary section
    assert "Total Requirements: 3" in contents
    assert "Tested: 2" in contents
    assert "Failures: 0" in contents

def test_traceability_matrix_determinism(tmp_path: Path):
    """
    Ensures identical inputs produce identical matrices.
    """

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"

    evidence_root.mkdir()

    create_dummy_requirements(req_yaml)
    create_dummy_evidence(evidence_root)

    matrix1 = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    matrix2 = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    assert matrix1 == matrix2
    
def test_duplicate_requirement_ids_detected(tmp_path: Path):
    """
    Requirement IDs must be unique.
    """

    req_yaml = tmp_path / "requirements.yaml"

    req_yaml.write_text(
        """
    requirements:
    - id: REQ-001
        description: A
    - id: REQ-001
        description: B
    """
        )

    with pytest.raises(Exception):
        validate_traceability(
            requirements_yaml=req_yaml,
            test_dir=tmp_path,
        )

def test_invalid_yaml_rejected(tmp_path: Path):
    """
    System should fail clearly on malformed YAML.
    """

    req_yaml = tmp_path / "requirements.yaml"

    req_yaml.write_text(":::: invalid yaml ::::")

    with pytest.raises(Exception):
        validate_traceability(
            requirements_yaml=req_yaml,
            test_dir=tmp_path,
        )

def test_unknown_requirement_in_evidence(tmp_path: Path):

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"

    evidence_root.mkdir()

    create_dummy_requirements(req_yaml)

    run_dir = evidence_root / "run"
    run_dir.mkdir()

    bad_record = {
        "test_id": "test_bad",
        "requirements": ["NON_EXISTENT_REQ"],
        "result": "PASS",
    }

    (run_dir / "bad.json").write_text(json.dumps(bad_record))

    matrix = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    # matrix should still build without crashing
    assert matrix

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
        "requirements": ["CAC-REQ-001"],
        "result": "FAIL",
    }

    (newer / "fail.json").write_text(json.dumps(record))

    matrix = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    matrix_by_id = {row["requirement_id"]: row for row in matrix}

    assert matrix_by_id["CAC-REQ-001"]["status"] == "FAIL"
    
def test_empty_evidence_directory(tmp_path: Path):

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"

    evidence_root.mkdir()

    create_dummy_requirements(req_yaml)

    matrix = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    statuses = [row["status"] for row in matrix]

    assert all(status == "UNTESTED" for status in statuses)
    
def test_invalid_requirement_id_format(tmp_path: Path):

    req_yaml = tmp_path / "requirements.yaml"

    req_yaml.write_text(
        """
requirements:
  - id: BADFORMAT
    description: invalid id
"""
    )

    with pytest.raises(Exception):
        validate_traceability(
            requirements_yaml=req_yaml,
            test_dir=tmp_path,
        )
    
def test_invalid_evidence_schema(tmp_path: Path):

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"

    evidence_root.mkdir()

    create_dummy_requirements(req_yaml)

    run = evidence_root / "run"
    run.mkdir()

    bad_record = {
        "requirements": ["CAC-REQ-001"]
    }

    (run / "bad.json").write_text(json.dumps(bad_record))

    matrix = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    assert matrix
    
def test_run_tests_and_trace_smoke(tmp_path):
    """
    Ensures CLI pipeline executes.
    """

    from regulatory_tools.testing import run_tests_and_trace

    project = tmp_path / "proj"
    project.mkdir()

    (project / "tests").mkdir()
    (project / "docs").mkdir()

    src = project / "src"
    src.mkdir()

    pkg = src / "dummy_pkg"
    pkg.mkdir()

    (pkg / "__init__.py").write_text("")

    create_dummy_requirements(project / "docs" / "requirements.yaml")

    run_tests_and_trace(project)