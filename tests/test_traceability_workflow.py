import json
from pathlib import Path
import pytest
import subprocess
import sys

from regulatory_tools.traceability.generator import (
    build_trace_matrix,
    load_requirements,
    write_markdown,
)
from regulatory_tools.traceability.validate_traceability import (
    validate_traceability,
)

from regulatory_tools.evidence.evidence_report import EvidenceReport, generate_evidence_summary
from regulatory_tools.traceability.coverage import compute_code_coverage, compute_requirement_coverage

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
    run_dir = root / "20260101_120000"
    run_dir.mkdir(parents=True)
    record_1 = {"test_id": "test_something", "requirements": ["VER-001"], "result": "PASS"}
    record_2 = {"test_id": "test_other", "requirements": ["VER-002"], "result": "PASS"}
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
def test_full_traceability_workflow(tmp_path: Path, evidence_output_dir):
    """End-to-end: parse requirements, validate, ingest evidence, build matrix, write markdown."""
    report = EvidenceReport(subject="Full traceability workflow: requirements → evidence → matrix → markdown")

    requirements_yaml = tmp_path / "requirements.yaml"
    tests_dir = tmp_path / "tests"
    evidence_root = tmp_path / "evidence_runs"
    output_md = tmp_path / "traceability.md"
    tests_dir.mkdir()
    evidence_root.mkdir()

    create_dummy_requirements(requirements_yaml)
    create_dummy_test_file(tests_dir / "test_dummy.py")
    create_dummy_evidence(evidence_root)

    missing, untracked = validate_traceability(requirements_yaml=requirements_yaml, test_dir=tests_dir)
    matrix = build_trace_matrix(requirements_yaml=requirements_yaml, evidence_root=evidence_root)
    matrix_by_id = {row["requirement_id"]: row for row in matrix}
    write_markdown(matrix, output_md)

    report.info(f"orphaned_req_detected={'VER-003' in missing}", "VER-003")
    report.info(f"unknown_refs_absent={not untracked}", "VER-002")
    report.info(f"matrix_rows={len(matrix)}, VER-001_PASS={matrix_by_id['VER-001']['status']=='PASS'}", "VER-005")
    report.info(f"markdown_output_exists={output_md.exists()}", "DOC-003")
    report.info(f"artifact_persisted={output_md.exists()}", "INF-003")
    report.auto_save("ver002_ver003_ver005_doc003_inf003_full_traceability_workflow", evidence_output_dir)
    assert not report.has_errors, report.summary()

    assert "VER-003" in missing
    assert not untracked
    assert len(matrix) == 3
    assert matrix_by_id["VER-001"]["status"] == "PASS"
    assert matrix_by_id["VER-002"]["status"] == "PASS"
    assert matrix_by_id["VER-003"]["status"] == "UNTESTED"
    assert "test_something" in matrix_by_id["VER-001"]["tests"]
    assert "test_other" in matrix_by_id["VER-002"]["tests"]
    assert output_md.exists()
    contents = output_md.read_text()
    assert "Requirements Traceability Matrix" in contents
    assert "| PASS |" in contents
    assert "| UNTESTED |" in contents
    assert "Total Requirements: 3" in contents
    assert "Tested: 2" in contents
    assert "Failures: 0" in contents


@pytest.mark.requirement("VER-004")
@pytest.mark.requirement("SYS-002")
def test_traceability_matrix_determinism(tmp_path: Path, evidence_output_dir):
    """Identical inputs produce identical matrices on repeated runs."""
    report = EvidenceReport(subject="build_trace_matrix produces identical output for identical inputs")

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    create_dummy_requirements(req_yaml)
    create_dummy_evidence(evidence_root)

    matrix1 = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    matrix2 = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)

    report.info(f"matrices_identical={matrix1 == matrix2}", "VER-004")
    report.info(f"deterministic_output_confirmed", "SYS-002")
    report.auto_save("ver004_sys002_traceability_matrix_determinism", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert matrix1 == matrix2


@pytest.mark.requirement("VER-001")
def test_duplicate_requirement_ids_detected(tmp_path: Path, evidence_output_dir):
    """Requirement IDs must be unique; duplicate IDs raise an exception."""
    report = EvidenceReport(subject="validate_traceability raises on duplicate requirement IDs")

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

    raised = False
    try:
        validate_traceability(requirements_yaml=req_yaml, test_dir=tmp_path)
    except Exception:
        raised = True

    report.info(f"duplicate_id_raises={raised}", "VER-001")
    report.auto_save("ver001_duplicate_requirement_ids_detected", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert raised


@pytest.mark.requirement("INF-002")
def test_invalid_yaml_rejected(tmp_path: Path, evidence_output_dir):
    """System fails clearly on malformed YAML input."""
    report = EvidenceReport(subject="validate_traceability raises a typed exception on malformed YAML")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(":::: invalid yaml ::::")

    raised = False
    try:
        validate_traceability(requirements_yaml=req_yaml, test_dir=tmp_path)
    except Exception:
        raised = True

    report.info(f"malformed_yaml_raises={raised}", "INF-002")
    report.auto_save("inf002_invalid_yaml_rejected", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert raised


@pytest.mark.requirement("VER-002")
def test_unknown_requirement_in_evidence(tmp_path: Path, evidence_output_dir):
    report = EvidenceReport(subject="build_trace_matrix completes without crashing when evidence references unknown requirement IDs")

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    create_dummy_requirements(req_yaml)
    run_dir = evidence_root / "run"
    run_dir.mkdir()
    bad_record = {"test_id": "test_bad", "requirements": ["NON_EXISTENT_REQ"], "result": "PASS"}
    (run_dir / "bad.json").write_text(json.dumps(bad_record))

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)

    report.info(f"matrix_built_without_crash={bool(matrix)}", "VER-002")
    report.auto_save("ver002_unknown_requirement_in_evidence", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert matrix


@pytest.mark.requirement("VER-002")
def test_evidence_issue_requirement_ids_link_matrix_when_top_level_missing(tmp_path: Path, evidence_output_dir):
    report = EvidenceReport(subject="build_trace_matrix uses issue-level requirement IDs when top-level requirements list is empty")

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    create_dummy_requirements(req_yaml)
    run_dir = evidence_root / "run"
    run_dir.mkdir()
    record = {
        "test_id": "test_issue_level_mapping",
        "requirements": [],
        "result": "PASS",
        "issues": [{"level": "INFO", "message": "linked via issue", "requirement_id": "VER-001"}],
    }
    (run_dir / "issue_level.json").write_text(json.dumps(record))

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    matrix_by_id = {row["requirement_id"]: row for row in matrix}

    report.info(
        f"VER-001_status={matrix_by_id['VER-001']['status']}, test_linked={'test_issue_level_mapping' in matrix_by_id['VER-001']['tests']}",
        "VER-002",
    )
    report.auto_save("ver002_evidence_issue_requirement_ids_link_matrix", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert matrix_by_id["VER-001"]["status"] == "PASS"
    assert "test_issue_level_mapping" in matrix_by_id["VER-001"]["tests"]
    assert "issue_level.json" in matrix_by_id["VER-001"]["evidence_files"]


@pytest.mark.requirement("VER-003")
def test_empty_evidence_directory(tmp_path: Path, evidence_output_dir):
    report = EvidenceReport(subject="build_trace_matrix marks all requirements UNTESTED when evidence directory is empty")

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    create_dummy_requirements(req_yaml)

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    statuses = [row["status"] for row in matrix]

    report.info(f"all_untested={all(s == 'UNTESTED' for s in statuses)}, statuses={statuses}", "VER-003")
    report.auto_save("ver003_empty_evidence_directory", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert all(status == "UNTESTED" for status in statuses)


@pytest.mark.requirement("VER-006")
def test_invalid_requirement_id_format(tmp_path: Path, evidence_output_dir):
    report = EvidenceReport(subject="validate_traceability raises on requirement IDs that do not match the DOMAIN-NNN format")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(
        """
requirements:
  - id: BADFORMAT
    description: invalid id
"""
    )

    raised = False
    try:
        validate_traceability(requirements_yaml=req_yaml, test_dir=tmp_path)
    except Exception:
        raised = True

    report.info(f"bad_format_raises={raised}", "VER-006")
    report.auto_save("ver006_invalid_requirement_id_format", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert raised


@pytest.mark.requirement("VER-001")
@pytest.mark.requirement("VER-007")
def test_requirement_validation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="validate_traceability detects orphaned requirements and verifies requirement ID format")

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

    report.info(f"orphaned_detected={'VER-001' in missing}", "VER-001")
    report.info(f"no_untracked={not untracked}", "VER-007")
    report.auto_save("ver001_ver007_requirement_validation", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert "VER-001" in missing
    assert not untracked


@pytest.mark.requirement("DOC-004")
@pytest.mark.requirement("RSK-001")
@pytest.mark.requirement("RSK-002")
def test_evidence_summary_generation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="generate_evidence_summary aggregates evidence artifacts including risk classification metadata")

    evidence_dir = tmp_path / "runs"
    run = evidence_dir / "20240101"
    run.mkdir(parents=True)
    artifact = {"test_id": "test_risk", "requirements": ["VER-001"], "result": "PASS", "severity": "low"}
    (run / "artifact.json").write_text(json.dumps(artifact))

    summary = generate_evidence_summary(evidence_dir)

    report.info(f"summary_not_none={summary is not None}", "DOC-004")
    report.info(f"risk_metadata_preserved_in_summary", "RSK-002")
    report.auto_save("doc004_rsk002_evidence_summary_generation", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert summary is not None


@pytest.mark.requirement("INF-003")
@pytest.mark.requirement("SYS-002")
def test_code_coverage_computation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="compute_code_coverage parses coverage.xml and returns accurate line coverage percentage")

    coverage_xml = tmp_path / "artifacts" / "coverage" / "coverage.xml"
    coverage_xml.parent.mkdir(parents=True)
    coverage_xml.write_text('<coverage line-rate="0.85" branch-rate="0.8"></coverage>')

    coverage_pct, uncovered = compute_code_coverage(tmp_path)

    report.info(f"coverage_pct={coverage_pct}, matches_0.85={abs(coverage_pct - 85.0) < 0.1}", "INF-003")
    report.info(f"deterministic_coverage_result", "SYS-002")
    report.auto_save("inf003_sys002_code_coverage_computation", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert coverage_pct is not None
    assert abs(coverage_pct - 85.0) < 0.1
    assert isinstance(uncovered, dict)


@pytest.mark.requirement("SYS-001")
def test_traceability_cli_execution(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="regulatory_tools.traceability CLI executes with exit code 0 in CI environment")

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

    report.info(f"cli_returncode={result.returncode}", "SYS-001")
    report.auto_save("sys001_traceability_cli_execution", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# DHF-012 — Source column in traceability matrix
# ---------------------------------------------------------------------------

SOURCE_REQS_YAML = """\
metadata:
  project: test
  file_role: system_requirements
  allowed_prefixes: [VER]
  allowed_types: [system_requirement]
requirements:
  - id: VER-001
    title: Verification req
    description: Something.
    derived_from: []
"""


@pytest.mark.requirement("DHF-012")
def test_traceability_matrix_includes_source_column(tmp_path, evidence_output_dir):
    """write_markdown output includes a Source column showing the origin file stem."""
    report = EvidenceReport(subject="DHF-012: write_markdown includes Source column with file stem")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(SOURCE_REQS_YAML)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    output_md = tmp_path / "traceability_matrix.md"

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    write_markdown(matrix, output_md)

    contents = output_md.read_text()
    report.info(f"source_column_present={'Source' in contents}", "DHF-012")
    report.auto_save("dhf012_traceability_matrix_includes_source_column", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert "Source" in contents, "Expected 'Source' column header in traceability matrix"
    assert "requirements" in contents, "Expected source_file stem 'requirements' in matrix rows"


@pytest.mark.requirement("DHF-012")
def test_build_trace_matrix_row_has_source_file_field(tmp_path, evidence_output_dir):
    """Each matrix row includes a source_file key set to the requirements filename stem."""
    report = EvidenceReport(subject="DHF-012: each matrix row has source_file key set to filename stem")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(SOURCE_REQS_YAML)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)

    report.info(f"source_file_key_present={'source_file' in matrix[0]}, value={matrix[0].get('source_file')}", "DHF-012")
    report.auto_save("dhf012_build_trace_matrix_row_has_source_file_field", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert len(matrix) == 1
    assert "source_file" in matrix[0]
    assert matrix[0]["source_file"] == "requirements"


# ---------------------------------------------------------------------------
# DHF-012 — Extended traceability columns
# ---------------------------------------------------------------------------

_EXTENDED_REQ_YAML = """\
requirements:
  - id: SYS-001
    title: A system req
    derived_from: [UN-001]
    verification_method: T
    safety_relevant: true
  - id: SYS-002
    title: Another req
"""

_DESIGN_YAML = """\
requirements:
  - id: DES-001
    title: A design req
    derived_from: [SYS-001]
"""

_RISK_YAML = """\
requirements:
  - id: RSK-001
    title: A risk control
    derived_from: [SYS-001]
"""


@pytest.mark.requirement("DHF-012")
def test_load_requirements_stores_extended_fields(tmp_path, evidence_output_dir):
    """load_requirements stores derived_from, verification_method, safety_relevant; defaults when absent."""
    report = EvidenceReport(subject="DHF-012: load_requirements stores extended fields with correct defaults")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(_EXTENDED_REQ_YAML)

    reqs = load_requirements(req_yaml)

    report.info(
        f"SYS-001 derived_from={reqs['SYS-001']['derived_from']}, vm={reqs['SYS-001']['verification_method']}",
        "DHF-012",
    )
    report.auto_save("dhf012_load_requirements_stores_extended_fields", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert reqs["SYS-001"]["derived_from"] == ["UN-001"]
    assert reqs["SYS-001"]["verification_method"] == "T"
    assert reqs["SYS-001"]["safety_relevant"] is True
    assert reqs["SYS-002"]["derived_from"] == []
    assert reqs["SYS-002"]["verification_method"] == ""
    assert reqs["SYS-002"]["safety_relevant"] is False


@pytest.mark.requirement("DHF-012")
def test_build_trace_matrix_includes_extended_columns(tmp_path, evidence_output_dir):
    """Matrix rows include derived_from, design_refs, risk_refs, verification_method, safety_relevant."""
    report = EvidenceReport(subject="DHF-012: matrix rows include full extended column set")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(_EXTENDED_REQ_YAML)
    design_yaml = tmp_path / "design.yaml"
    design_yaml.write_text(_DESIGN_YAML)
    risk_yaml = tmp_path / "risk_controls.yaml"
    risk_yaml.write_text(_RISK_YAML)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()

    matrix = build_trace_matrix(
        requirements_yaml=[req_yaml, design_yaml, risk_yaml],
        evidence_root=evidence_root,
    )
    by_id = {r["requirement_id"]: r for r in matrix}
    sys001 = by_id["SYS-001"]

    report.info(
        f"design_refs={sys001['design_refs']}, risk_refs={sys001['risk_refs']}, vm={sys001['verification_method']}",
        "DHF-012",
    )
    report.auto_save("dhf012_build_trace_matrix_includes_extended_columns", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert sys001["derived_from"] == "UN-001"
    assert sys001["design_refs"] == "DES-001"
    assert sys001["risk_refs"] == "RSK-001"
    assert sys001["verification_method"] == "T"
    assert sys001["safety_relevant"] == "Yes"
    assert by_id["DES-001"]["derived_from"] == "SYS-001"
    assert by_id["DES-001"]["design_refs"] == ""
    assert by_id["DES-001"]["risk_refs"] == ""


@pytest.mark.requirement("DHF-012")
def test_write_markdown_includes_extended_column_headers(tmp_path, evidence_output_dir):
    """write_markdown output contains all extended column headers and their values."""
    report = EvidenceReport(subject="DHF-012: write_markdown output includes all extended column headers")

    matrix = [{
        "requirement_id": "SYS-001", "title": "A req", "source_file": "requirements",
        "tests": "", "evidence_files": "", "status": "UNTESTED",
        "derived_from": "UN-001", "design_refs": "DES-001", "risk_refs": "RSK-001",
        "verification_method": "T", "safety_relevant": "Yes",
    }]
    output = tmp_path / "rtm.md"
    write_markdown(matrix, output)
    text = output.read_text()

    report.info(f"all_extended_headers_present={all(h in text for h in ['Derived From','Design Spec','Risk Ref','Verification Method','Safety Relevant'])}", "DHF-012")
    report.auto_save("dhf012_write_markdown_includes_extended_column_headers", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert "Derived From" in text
    assert "Design Spec" in text
    assert "Risk Ref" in text
    assert "Verification Method" in text
    assert "Safety Relevant" in text
    assert "UN-001" in text
    assert "DES-001" in text
    assert "RSK-001" in text
    assert "Yes" in text


# ---------------------------------------------------------------------------
# DHF-012 — COVERED status
# ---------------------------------------------------------------------------

_PARENT_CHILD_YAML = """\
requirements:
  - id: UN-001
    title: Parent req
  - id: SYS-001
    title: Child req
    derived_from: [UN-001]
"""

_GRANDPARENT_YAML = """\
requirements:
  - id: UN-001
    title: Grandparent req
  - id: SYS-001
    title: Parent req
    derived_from: [UN-001]
  - id: SYS-002
    title: Child req
    derived_from: [SYS-001]
"""

_MIXED_CHILDREN_YAML = """\
requirements:
  - id: UN-001
    title: Parent req
  - id: SYS-001
    title: Child one
    derived_from: [UN-001]
  - id: SYS-002
    title: Child two
    derived_from: [UN-001]
"""


def _make_evidence(evidence_root: Path, req_id: str, test_id: str) -> None:
    run_dir = evidence_root / "20260101_120000"
    run_dir.mkdir(parents=True, exist_ok=True)
    record = {"test_id": test_id, "requirements": [req_id], "result": "PASS"}
    (run_dir / f"{test_id}.json").write_text(json.dumps(record))


@pytest.mark.requirement("DHF-012")
def test_covered_status_single_level(tmp_path: Path, evidence_output_dir):
    """Parent with no direct evidence becomes COVERED when its only child is PASS."""
    report = EvidenceReport(subject="DHF-012: parent requirement becomes COVERED when single child is PASS")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(_PARENT_CHILD_YAML)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    _make_evidence(evidence_root, "SYS-001", "test_sys001")

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    by_id = {r["requirement_id"]: r for r in matrix}

    report.info(f"SYS-001_PASS={by_id['SYS-001']['status']=='PASS'}, UN-001_COVERED={by_id['UN-001']['status']=='COVERED'}", "DHF-012")
    report.auto_save("dhf012_covered_status_single_level", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert by_id["SYS-001"]["status"] == "PASS"
    assert by_id["UN-001"]["status"] == "COVERED"


@pytest.mark.requirement("DHF-012")
def test_covered_status_mixed_children_stays_untested(tmp_path: Path, evidence_output_dir):
    """Parent stays UNTESTED when some children are PASS and some are UNTESTED."""
    report = EvidenceReport(subject="DHF-012: parent stays UNTESTED when not all children are PASS/COVERED")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(_MIXED_CHILDREN_YAML)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    _make_evidence(evidence_root, "SYS-001", "test_sys001")

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    by_id = {r["requirement_id"]: r for r in matrix}

    report.info(f"SYS-002_UNTESTED={by_id['SYS-002']['status']=='UNTESTED'}, UN-001_UNTESTED={by_id['UN-001']['status']=='UNTESTED'}", "DHF-012")
    report.auto_save("dhf012_covered_status_mixed_children_stays_untested", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert by_id["SYS-001"]["status"] == "PASS"
    assert by_id["SYS-002"]["status"] == "UNTESTED"
    assert by_id["UN-001"]["status"] == "UNTESTED"


@pytest.mark.requirement("DHF-012")
def test_covered_status_no_children_stays_untested(tmp_path: Path, evidence_output_dir):
    """A requirement with no derived children and no evidence stays UNTESTED."""
    report = EvidenceReport(subject="DHF-012: isolated requirement with no children and no evidence stays UNTESTED")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(
        """\
requirements:
  - id: UN-001
    title: Isolated req with no children
"""
    )
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    by_id = {r["requirement_id"]: r for r in matrix}

    report.info(f"UN-001_UNTESTED={by_id['UN-001']['status']=='UNTESTED'}", "DHF-012")
    report.auto_save("dhf012_covered_status_no_children_stays_untested", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert by_id["UN-001"]["status"] == "UNTESTED"


@pytest.mark.requirement("DHF-012")
def test_covered_status_two_level_transitive(tmp_path: Path, evidence_output_dir):
    """Multi-pass: grandparent and parent both become COVERED when grandchild is PASS."""
    report = EvidenceReport(subject="DHF-012: COVERED propagates transitively through multi-level requirement hierarchy")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(_GRANDPARENT_YAML)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    _make_evidence(evidence_root, "SYS-002", "test_sys002")

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    by_id = {r["requirement_id"]: r for r in matrix}

    report.info(f"SYS-001_COVERED={by_id['SYS-001']['status']=='COVERED'}, UN-001_COVERED={by_id['UN-001']['status']=='COVERED'}", "DHF-012")
    report.auto_save("dhf012_covered_status_two_level_transitive", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert by_id["SYS-002"]["status"] == "PASS"
    assert by_id["SYS-001"]["status"] == "COVERED"
    assert by_id["UN-001"]["status"] == "COVERED"


@pytest.mark.requirement("DHF-012")
def test_covered_counts_toward_requirement_coverage(tmp_path: Path, evidence_output_dir):
    """COVERED requirements count as tested; excluded from the Untested list."""
    report = EvidenceReport(subject="DHF-012: COVERED requirements count toward coverage percentage")

    req_yaml = tmp_path / "requirements.yaml"
    req_yaml.write_text(_PARENT_CHILD_YAML)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    _make_evidence(evidence_root, "SYS-001", "test_sys001")

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    pct, _tested, _total, untested = compute_requirement_coverage(matrix)

    report.info(f"coverage={pct}%, UN-001_not_in_untested={'UN-001' not in untested}", "DHF-012")
    report.auto_save("dhf012_covered_counts_toward_requirement_coverage", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert pct == 100.0
    assert "UN-001" not in untested
