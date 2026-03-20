import json
from pathlib import Path
from importlib_resources import contents
import pytest
import subprocess
import sys

from regulatory_tools.traceability.generator import (
    build_trace_matrix,
    write_markdown,
)
from regulatory_tools.traceability.validate_traceability import (
    validate_traceability,
)

from regulatory_tools.evidence.evidence_report import generate_evidence_summary
from regulatory_tools.traceability.coverage import compute_code_coverage

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


def create_dummy_test_file(path: Path):
    path.write_text(
        '''
def requirement(req_id):
    pass

def test_something():
    requirement("VER-001")
    assert True

def test_other():
    requirement("VER-002")
    assert True
'''
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
@pytest.mark.requirement("VER-002")
@pytest.mark.requirement("VER-003")
@pytest.mark.requirement("VER-005")
@pytest.mark.requirement("DOC-003")
@pytest.mark.requirement("INF-003")
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

    # VER-003 declared but not referenced in tests
    assert "VER-003" in missing

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
    assert matrix_by_id["VER-001"]["status"] == "PASS"
    assert matrix_by_id["VER-002"]["status"] == "PASS"

    # Untested requirement
    assert matrix_by_id["VER-003"]["status"] == "UNTESTED"

    # Ensure linked tests recorded
    assert "test_something" in matrix_by_id["VER-001"]["tests"]
    assert "test_other" in matrix_by_id["VER-002"]["tests"]

    # --- Write markdown output
    write_markdown(matrix, output_md)

    assert output_md.exists()

    contents = output_md.read_text()

    # Matrix structure
    assert "Requirements Traceability Matrix" in contents
    assert "VER-001" in contents
    assert "VER-002" in contents
    assert "VER-003" in contents

    # Status values
    assert "| PASS |" in contents
    assert "| UNTESTED |" in contents

    # Summary section
    assert "Total Requirements: 3" in contents
    assert "Tested: 2" in contents
    assert "Failures: 0" in contents

@pytest.mark.requirement("VER-004")
@pytest.mark.requirement("SYS-002")
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

@pytest.mark.requirement("VER-001")
def test_duplicate_requirement_ids_detected(tmp_path: Path):
    """
    Requirement IDs must be unique.
    """

    req_yaml = tmp_path / "requirements.yaml"

    req_yaml.write_text(
        """
    requirements:
    - id: VER-001
        description: A
    - id: VER-001
        description: B
    """
        )

    with pytest.raises(Exception):
        validate_traceability(
            requirements_yaml=req_yaml,
            test_dir=tmp_path,
        )
        
@pytest.mark.requirement("INF-002")
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

@pytest.mark.requirement("VER-002")
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


@pytest.mark.requirement("VER-003")
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

@pytest.mark.requirement("VER-006")
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
# ------------------------------------------------
# Requirement validation edge cases
# ------------------------------------------------

@pytest.mark.requirement("VER-001")
@pytest.mark.requirement("VER-007")
def test_requirement_validation(tmp_path):

    req_file = tmp_path / "requirements.yaml"

    req_file.write_text(
        """
requirements:
  - id: VER-001
    description: test
"""
    )

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    missing, untracked = validate_traceability(req_file, tests_dir)

    assert "VER-001" in missing
    assert not untracked


# ------------------------------------------------
# Evidence summary generation
# ------------------------------------------------

@pytest.mark.requirement("DOC-004")
@pytest.mark.requirement("RSK-001")
@pytest.mark.requirement("RSK-002")
def test_evidence_summary_generation(tmp_path):

    evidence_dir = tmp_path / "runs"
    run = evidence_dir / "20240101"
    run.mkdir(parents=True)

    artifact = {
        "test_id": "test_risk",
        "requirements": ["VER-001"],
        "result": "PASS",
        "severity": "low",
    }

    (run / "artifact.json").write_text(json.dumps(artifact))

    summary = generate_evidence_summary(evidence_dir)

    assert summary is not None


# ------------------------------------------------
# Coverage calculation
# ------------------------------------------------

@pytest.mark.requirement("INF-003")
@pytest.mark.requirement("SYS-002")
def test_code_coverage_computation(tmp_path):

    coverage_file = tmp_path / "coverage.xml"

    coverage_file.write_text(
        """
<coverage line-rate="0.85" branch-rate="0.8">
</coverage>
"""
    )

    result = compute_code_coverage(coverage_file)

    assert result is not None


# ------------------------------------------------
# CLI execution
# ------------------------------------------------

@pytest.mark.requirement("SYS-001")
def test_traceability_cli_execution(tmp_path):

    project = tmp_path / "proj"
    project.mkdir()

    (project / "docs").mkdir()
    (project / "tests").mkdir()

    (project / "docs" / "requirements.yaml").write_text(
        """
requirements:
  - id: VER-001
    description: example
"""
    )

    result = subprocess.run(
        [sys.executable, "-m", "regulatory_tools.traceability", str(project)],
        capture_output=True,
    )

    assert result.returncode == 0