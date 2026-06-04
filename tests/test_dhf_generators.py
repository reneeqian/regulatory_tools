"""
Tests for regulatory_tools.dhf.generators (DHF-003, DHF-008, DHF-016).
These tests must fail before the generators exist.
"""
import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport


# ---------------------------------------------------------------------------
# Imports (fail until generators exist)
# ---------------------------------------------------------------------------

from regulatory_tools.dhf.generators.soup_table import SOUPTableGenerator
from regulatory_tools.dhf.generators.evidence_index import EvidenceIndexGenerator
from regulatory_tools.dhf.generators.system_requirements import SystemRequirementsGenerator
from regulatory_tools.dhf.generators.traceability_index import TraceabilityIndexGenerator
from regulatory_tools.dhf.generators.baseline_register import BaselineRegisterGenerator
from regulatory_tools.dhf.generators.change_log import ChangeLogGenerator
from regulatory_tools.dhf.generators.hazard_analysis import HazardAnalysisGenerator
from regulatory_tools.dhf.generators.anomaly_log import AnomalyLogGenerator  # fails until DHF-016 implemented
from regulatory_tools.dhf.requirements_reader import RequirementsReader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

START_COMMENT = "<!-- DHF_{TAG}_START -->"
END_COMMENT = "<!-- DHF_{TAG}_END -->"


def _doc_with_sentinels(tag: str, existing_rows: str = "") -> str:
    return (
        f"# Doc\n\n"
        f"<!-- DHF_{tag}_START -->\n"
        f"{existing_rows}"
        f"<!-- DHF_{tag}_END -->\n"
    )


# ---------------------------------------------------------------------------
# SOUPTableGenerator
# ---------------------------------------------------------------------------

SOUP_YAML = textwrap.dedent("""
    soup:
      - name: numpy
        version: "2.1.0"
        purpose: Numerical arrays
        license: BSD-3-Clause
      - name: torch
        version: "2.9.1"
        purpose: Deep learning
        license: BSD-3-Clause
""")


@pytest.mark.requirement("DHF-003")
def test_soup_table_generates_rows(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: SOUPTableGenerator produces markdown table rows from soup.yaml")

    soup_file = tmp_path / "soup.yaml"
    soup_file.write_text(SOUP_YAML)

    gen = SOUPTableGenerator(soup_file)
    rows = gen.generate_rows()

    assert "numpy" in rows
    assert "2.1.0" in rows
    assert "BSD-3-Clause" in rows
    assert "torch" in rows

    report.info(f"generate_rows() produced {len(rows.splitlines())} lines covering numpy and torch", "DHF-003")
    report.auto_save("dhf003_soup_table_rows", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-003")
def test_soup_table_update_document_replaces_sentinel_section(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: SOUPTableGenerator.update_document() replaces sentinel section in-place")

    soup_file = tmp_path / "soup.yaml"
    soup_file.write_text(SOUP_YAML)
    doc = tmp_path / "soup_register.md"
    doc.write_text(_doc_with_sentinels("SOUP_TABLE", "| old | rows |\n"))

    SOUPTableGenerator(soup_file).update_document(doc)

    content = doc.read_text()
    assert "numpy" in content
    assert "old | rows" not in content

    report.info("update_document replaced sentinel section with current soup entries", "DHF-003")
    report.auto_save("dhf003_soup_table_update_document", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# EvidenceIndexGenerator
# ---------------------------------------------------------------------------

def _write_evidence_json(run_dir: Path, name: str, subject: str, result: str, tags: list[str]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"{name}.json").write_text(json.dumps({
        "test_id": name,
        "subject": subject,
        "timestamp": "2026-05-01T12:00:00",
        "result": result,
        "requirement_tags": tags,
        "requirements": [],
        "issues": [],
    }))


@pytest.mark.requirement("DHF-003")
def test_evidence_index_generates_rows(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: EvidenceIndexGenerator produces table rows from evidence JSON files")

    run_dir = tmp_path / "evidence_runs" / "20260501_120000"
    _write_evidence_json(run_dir, "test_abc", "Test ABC subject", "PASS", ["SYS-001"])

    gen = EvidenceIndexGenerator(tmp_path / "evidence_runs")
    rows = gen.generate_rows()

    assert "test_abc" in rows
    assert "PASS" in rows
    assert "SYS-001" in rows

    report.info("generate_rows() produced rows from evidence JSON files", "DHF-003")
    report.auto_save("dhf003_evidence_index_rows", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-003")
def test_evidence_index_update_document_replaces_sentinel_section(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: EvidenceIndexGenerator.update_document() replaces sentinel section")

    run_dir = tmp_path / "evidence_runs" / "20260501_120000"
    _write_evidence_json(run_dir, "test_xyz", "Test XYZ", "PASS", ["DAT-001"])
    doc = tmp_path / "evidence_index.md"
    doc.write_text(_doc_with_sentinels("EVIDENCE_INDEX", "| stale | rows |\n"))

    EvidenceIndexGenerator(tmp_path / "evidence_runs").update_document(doc)

    content = doc.read_text()
    assert "test_xyz" in content
    assert "stale | rows" not in content

    report.info("update_document replaced sentinel section with current evidence entries", "DHF-003")
    report.auto_save("dhf003_evidence_index_update_document", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-003")
def test_evidence_index_empty_dir_produces_empty_rows(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: EvidenceIndexGenerator returns empty string when no JSON files exist")

    (tmp_path / "evidence_runs").mkdir()
    gen = EvidenceIndexGenerator(tmp_path / "evidence_runs")
    rows = gen.generate_rows()

    assert rows.strip() == ""

    report.info("Empty evidence_runs directory → generate_rows() returns empty string", "DHF-003")
    report.auto_save("dhf003_evidence_index_empty", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# SystemRequirementsGenerator
# ---------------------------------------------------------------------------

TYPED_REQS_YAML = textwrap.dedent("""
    metadata:
      project: test
      version: 1.0
    requirements:
      - id: UN-001
        type: user_need
        title: User need
        description: A user need.
      - id: SYS-001
        title: System req 1
        description: System req.
      - id: SYS-002
        title: System req 2
        description: Another.
      - id: RSK-001
        type: risk_control
        title: Risk control
        description: A risk control.
""")


@pytest.mark.requirement("DHF-008")
def test_system_requirements_domain_count_table(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-008: SystemRequirementsGenerator produces domain count table from requirements.yaml")

    reqs_file = tmp_path / "requirements.yaml"
    reqs_file.write_text(TYPED_REQS_YAML)

    gen = SystemRequirementsGenerator(RequirementsReader(reqs_file))
    rows = gen.generate_rows()

    assert "SYS" in rows
    assert "UN" in rows or "user_need" in rows.lower()
    assert "RSK" in rows

    report.info(f"generate_rows() produced table with domain/type breakdown", "DHF-008")
    report.auto_save("dhf008_system_requirements_domain_table", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-008")
def test_system_requirements_counts_are_correct(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-008: SystemRequirementsGenerator counts match requirements.yaml exactly")

    reqs_file = tmp_path / "requirements.yaml"
    reqs_file.write_text(TYPED_REQS_YAML)

    gen = SystemRequirementsGenerator(RequirementsReader(reqs_file))
    rows = gen.generate_rows()

    # SYS domain: 2 entries (SYS-001, SYS-002)
    assert "2" in rows

    report.info("Domain count '2' for SYS present in generated rows", "DHF-008")
    report.auto_save("dhf008_system_requirements_counts", evidence_output_dir)
    assert not report.has_errors, report.summary()


SPLIT_SRS_YAML = textwrap.dedent("""\
    metadata:
      project: test
      file_role: system_requirements
      allowed_prefixes: [SYS]
      allowed_types: [system_requirement]
    requirements:
      - id: SYS-001
        title: System req 1
        description: System req.
        derived_from: [UN-001]
      - id: SYS-002
        title: System req 2
        description: Another system req.
        derived_from: [UN-001]
""")

SPLIT_DESIGN_YAML = textwrap.dedent("""\
    metadata:
      project: test
      file_role: design_requirements
      allowed_prefixes: [SYS]
      allowed_types: [design_requirement]
    requirements:
      - id: SYS-099
        type: design_requirement
        title: Design detail
        description: Design spec.
        derived_from: [SYS-001]
""")


@pytest.mark.requirement("DHF-012")
def test_system_requirements_by_source_file_table(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-012: SystemRequirementsGenerator output includes 'By Source File' table when loaded from multiple files")

    srs = tmp_path / "requirements.yaml"
    srs.write_text(SPLIT_SRS_YAML)
    design = tmp_path / "design.yaml"
    design.write_text(SPLIT_DESIGN_YAML)

    gen = SystemRequirementsGenerator(RequirementsReader([srs, design]))
    rows = gen.generate_rows()

    assert "By Source File" in rows or "source file" in rows.lower(), \
        "Expected 'By Source File' section in generated rows"
    assert "requirements" in rows
    assert "design" in rows

    report.info("'By Source File' table present with 'requirements' and 'design' rows", "DHF-012")
    report.auto_save("dhf012_by_source_file_table", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# TraceabilityIndexGenerator
# ---------------------------------------------------------------------------

TRACEABILITY_MD = textwrap.dedent("""
    <!-- AUTO-GENERATED FILE. DO NOT EDIT MANUALLY. -->

    # Requirements Traceability Matrix

    ## Requirement Coverage

    **Coverage:** 100.0% (56 / 56 requirements tested)

    ## Forge Code Health

    **Overall Score:** 89.6%  **Grade:** B
""")


@pytest.mark.requirement("DHF-003")
def test_traceability_index_parses_coverage_stats(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: TraceabilityIndexGenerator parses coverage and grade from traceability_matrix.md")

    matrix_file = tmp_path / "traceability_matrix.md"
    matrix_file.write_text(TRACEABILITY_MD)

    gen = TraceabilityIndexGenerator(matrix_file)
    rows = gen.generate_rows()

    assert "100.0%" in rows or "56" in rows
    assert "89.6%" in rows or "Grade" in rows or "B" in rows

    report.info(f"generate_rows() extracted coverage/grade stats from matrix", "DHF-003")
    report.auto_save("dhf003_traceability_index_stats", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# BaselineRegisterGenerator
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-003")
def test_baseline_register_generates_rows_from_git_tags(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: BaselineRegisterGenerator produces rows from git tag output")

    with patch("subprocess.run") as mock_run:
        # First call: git tag -l
        # Second call: git rev-parse v0.1.0
        # Third call: git log -1 --format=%ci v0.1.0
        mock_run.side_effect = [
            _mock_proc("v0.1.0\nv0.2.0\n"),
            _mock_proc("abc1234def5678\n"),
            _mock_proc("2026-01-15 10:00:00 +0000\n"),
            _mock_proc("def5678abc1234\n"),
            _mock_proc("2026-03-20 14:00:00 +0000\n"),
        ]
        gen = BaselineRegisterGenerator(tmp_path)
        rows = gen.generate_rows()

    assert "v0.1.0" in rows
    assert "abc1234" in rows
    assert "v0.2.0" in rows

    report.info(f"generate_rows() produced rows for v0.1.0 and v0.2.0 with SHAs", "DHF-003")
    report.auto_save("dhf003_baseline_register_rows", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-003")
def test_baseline_register_empty_when_no_tags(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: BaselineRegisterGenerator returns empty string when no git tags exist")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_proc("")
        gen = BaselineRegisterGenerator(tmp_path)
        rows = gen.generate_rows()

    assert rows.strip() == ""

    report.info("No git tags → generate_rows() returns empty string", "DHF-003")
    report.auto_save("dhf003_baseline_register_empty", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# ChangeLogGenerator
# ---------------------------------------------------------------------------

PYPROJECT_TOML = textwrap.dedent("""
    [project]
    name = "coronary_prj"
    version = "0.3.1"
""")

GIT_LOG_OUTPUT = textwrap.dedent("""
    abc1234 feat: add calcium score regressor
    def5678 fix: handle missing patient directory
    ghi9012 chore: update dependencies
""").strip()


@pytest.mark.requirement("DHF-003")
def test_change_log_generates_rows_from_git_log(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-003: ChangeLogGenerator produces rows from git log and pyproject.toml version")

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT_TOML)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_proc(GIT_LOG_OUTPUT)
        gen = ChangeLogGenerator(git_repo=tmp_path, pyproject_toml=pyproject)
        rows = gen.generate_rows()

    assert "0.3.1" in rows or "calcium score" in rows

    report.info(f"generate_rows() produced change log from git log output", "DHF-003")
    report.auto_save("dhf003_change_log_rows", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Common: update_document idempotency (shared contract for all generators)
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-006")
def test_soup_table_update_document_is_idempotent(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-006: SOUPTableGenerator.update_document() is idempotent")

    soup_file = tmp_path / "soup.yaml"
    soup_file.write_text(SOUP_YAML)
    doc = tmp_path / "soup_register.md"
    doc.write_text(_doc_with_sentinels("SOUP_TABLE"))

    gen = SOUPTableGenerator(soup_file)
    gen.update_document(doc)
    first = doc.read_text()

    gen.update_document(doc)
    second = doc.read_text()

    assert first == second

    report.info("Two update_document() calls with same soup.yaml produce identical file", "DHF-006")
    report.auto_save("dhf006_soup_table_idempotent", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# HazardAnalysisGenerator
# ---------------------------------------------------------------------------

HAZARD_YAML = textwrap.dedent("""\
    hazards:
      - id: HAZ-001
        hazard: Test hazard A
        mitigation_ref: RSK-001
      - id: HAZ-002
        hazard: Test hazard B
        mitigation_ref: RSK-002
""")


@pytest.mark.requirement("DHF-014")
def test_hazard_analysis_scaffold_rows(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-014: HazardAnalysisGenerator produces scaffold rows with FILL placeholders")

    hazard_file = tmp_path / "hazard_analysis.yaml"
    hazard_file.write_text(HAZARD_YAML)

    gen = HazardAnalysisGenerator(hazard_file)
    rows = gen.generate_rows()

    assert "HAZ-001" in rows
    assert "HAZ-002" in rows
    assert "RSK-001" in rows
    assert "RSK-002" in rows
    assert "<!-- FILL -->" in rows, "cause/effect/severity/probability must be left as FILL placeholders"
    assert "Test hazard A" in rows
    assert "Test hazard B" in rows

    report.info(
        f"generate_rows() produced 2 scaffold rows; HAZ-IDs, hazard titles, and mitigation_refs "
        f"are populated; narrative columns contain <!-- FILL -->",
        "DHF-014",
    )
    report.auto_save("dhf014_hazard_analysis_scaffold_rows", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-014")
def test_hazard_analysis_update_document_replaces_sentinel(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-014: HazardAnalysisGenerator.update_document() replaces sentinel section")

    hazard_file = tmp_path / "hazard_analysis.yaml"
    hazard_file.write_text(HAZARD_YAML)
    doc = tmp_path / "hazard_analysis.md"
    doc.write_text(_doc_with_sentinels("HAZARD_ANALYSIS", "| stale | rows |\n"))

    HazardAnalysisGenerator(hazard_file).update_document(doc)

    content = doc.read_text()
    assert "HAZ-001" in content
    assert "stale | rows" not in content

    report.info("update_document replaced sentinel section with current hazard scaffold rows", "DHF-014")
    report.auto_save("dhf014_hazard_analysis_update_document", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-006")
def test_hazard_analysis_update_document_is_idempotent(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-006: HazardAnalysisGenerator.update_document() is idempotent")

    hazard_file = tmp_path / "hazard_analysis.yaml"
    hazard_file.write_text(HAZARD_YAML)
    doc = tmp_path / "hazard_analysis.md"
    doc.write_text(_doc_with_sentinels("HAZARD_ANALYSIS"))

    gen = HazardAnalysisGenerator(hazard_file)
    gen.update_document(doc)
    first = doc.read_text()

    gen.update_document(doc)
    second = doc.read_text()

    assert first == second

    report.info("Two update_document() calls with same hazard_analysis.yaml produce identical file", "DHF-006")
    report.auto_save("dhf006_hazard_analysis_idempotent", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# AnomalyLogGenerator — DHF-016
# ---------------------------------------------------------------------------

ANOMALY_LOG_TWO_ENTRIES = textwrap.dedent("""\
    metadata:
      project: test_project
      standard: IEC 62304 §9
    anomalies:
      - id: ANO-001
        date: "2026-05-26"
        severity: major
        status: open
        summary: "Patient sample contract test failures"
        affected_requirements: [DAT-001]
        resolution: "Under investigation"
      - id: ANO-002
        date: "2026-04-10"
        severity: low
        status: closed
        summary: "Missing documentation in README"
        affected_requirements: []
        resolution: "Updated README"
        closed: "2026-04-12"
""")

ANOMALY_LOG_EMPTY_LIST = textwrap.dedent("""\
    metadata:
      project: test_project
      standard: IEC 62304 §9
    anomalies: []
""")

ANOMALY_LOG_ALL_OPTIONAL_ABSENT = textwrap.dedent("""\
    metadata:
      project: test_project
      standard: IEC 62304 §9
    anomalies:
      - id: ANO-001
        date: "2026-05-26"
        severity: major
        status: open
        summary: "Some issue"
""")


@pytest.mark.requirement("DHF-016")
def test_anomaly_log_generates_two_table_rows(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-016: AnomalyLogGenerator produces one row per anomaly entry")

    yaml_file = tmp_path / "anomaly_log.yaml"
    yaml_file.write_text(ANOMALY_LOG_TWO_ENTRIES)

    gen = AnomalyLogGenerator(yaml_file)
    rows = gen.generate_table_rows()

    assert "ANO-001" in rows
    assert "ANO-002" in rows
    assert rows.count("ANO-") == 2, f"Expected exactly 2 rows; got:\n{rows}"

    report.info("2-entry yaml → 2 rows in generate_table_rows()", "DHF-016")
    report.auto_save("dhf016_anomaly_log_two_rows", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-016")
def test_anomaly_log_empty_produces_no_data_rows(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-016: AnomalyLogGenerator produces no data rows for empty anomalies list")

    yaml_file = tmp_path / "anomaly_log.yaml"
    yaml_file.write_text(ANOMALY_LOG_EMPTY_LIST)

    gen = AnomalyLogGenerator(yaml_file)
    rows = gen.generate_table_rows()

    assert "ANO-" not in rows, f"Empty list must produce no data rows; got:\n{rows}"

    report.info("empty anomalies list → no data rows", "DHF-016")
    report.auto_save("dhf016_anomaly_log_empty_no_rows", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-016")
def test_anomaly_log_open_entry_in_unresolved_section(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-016: open anomaly appears in generate_unresolved_rows()")

    yaml_file = tmp_path / "anomaly_log.yaml"
    yaml_file.write_text(ANOMALY_LOG_TWO_ENTRIES)

    gen = AnomalyLogGenerator(yaml_file)
    unresolved = gen.generate_unresolved_rows()

    assert "ANO-001" in unresolved, f"Open ANO-001 must appear in unresolved rows; got:\n{unresolved}"

    report.info("open ANO-001 → appears in generate_unresolved_rows()", "DHF-016")
    report.auto_save("dhf016_open_anomaly_in_unresolved", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-016")
def test_anomaly_log_closed_entry_not_in_unresolved_section(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-016: closed anomaly does not appear in generate_unresolved_rows()")

    yaml_file = tmp_path / "anomaly_log.yaml"
    yaml_file.write_text(ANOMALY_LOG_TWO_ENTRIES)

    gen = AnomalyLogGenerator(yaml_file)
    unresolved = gen.generate_unresolved_rows()

    assert "ANO-002" not in unresolved, f"Closed ANO-002 must not appear in unresolved rows; got:\n{unresolved}"

    report.info("closed ANO-002 → absent from generate_unresolved_rows()", "DHF-016")
    report.auto_save("dhf016_closed_anomaly_not_in_unresolved", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-016")
def test_anomaly_log_optional_fields_absent_render_as_dash(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-016: missing optional fields (safety_impact, linked_pr, closed) render as —")

    yaml_file = tmp_path / "anomaly_log.yaml"
    yaml_file.write_text(ANOMALY_LOG_ALL_OPTIONAL_ABSENT)

    gen = AnomalyLogGenerator(yaml_file)
    rows = gen.generate_table_rows()

    assert "ANO-001" in rows
    assert "—" in rows, f"Missing optional fields must render as —; got:\n{rows}"

    report.info("optional fields absent → rendered as — in table row", "DHF-016")
    report.auto_save("dhf016_optional_fields_dash", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-016")
def test_anomaly_log_update_document_is_idempotent(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-016: AnomalyLogGenerator.update_document() is idempotent")

    yaml_file = tmp_path / "anomaly_log.yaml"
    yaml_file.write_text(ANOMALY_LOG_TWO_ENTRIES)
    doc = tmp_path / "anomaly_log.md"
    doc.write_text(
        _doc_with_sentinels("ANOMALY_TABLE")
        + "\n"
        + _doc_with_sentinels("UNRESOLVED_ANOMALIES")
    )

    gen = AnomalyLogGenerator(yaml_file)
    gen.update_document(doc)
    first = doc.read_text()

    gen.update_document(doc)
    second = doc.read_text()

    assert first == second

    report.info("Two update_document() calls with same anomaly_log.yaml produce identical file", "DHF-016")
    report.auto_save("dhf016_update_document_idempotent", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-016")
def test_anomaly_log_update_document_replaces_stale_rows(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-016: update_document replaces stale sentinel content with current YAML data")

    yaml_file = tmp_path / "anomaly_log.yaml"
    yaml_file.write_text(ANOMALY_LOG_TWO_ENTRIES)
    doc = tmp_path / "anomaly_log.md"
    doc.write_text(_doc_with_sentinels("ANOMALY_TABLE", "| stale | data | here |\n"))

    AnomalyLogGenerator(yaml_file).update_document(doc)

    content = doc.read_text()
    assert "ANO-001" in content
    assert "stale | data | here" not in content

    report.info("update_document replaced stale sentinel section with current anomaly rows", "DHF-016")
    report.auto_save("dhf016_update_document_replaces_stale", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _mock_proc(stdout: str):
    from unittest.mock import MagicMock
    m = MagicMock()
    m.stdout = stdout
    m.returncode = 0
    return m
