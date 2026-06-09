"""Tests for check_anomaly_log() — VER-010.
These tests fail until anomaly_checker.py is implemented.
"""

import textwrap

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.quality.anomaly_checker import check_anomaly_log

REQUIREMENTS_SAMD_C = textwrap.dedent("""\
    metadata:
      project: test_project
      samd_class: C
    requirements: []
""")

REQUIREMENTS_SAMD_B = textwrap.dedent("""\
    metadata:
      project: test_project
      samd_class: B
    requirements: []
""")

REQUIREMENTS_SAMD_TOOL = textwrap.dedent("""\
    metadata:
      project: test_project
      samd_class: tool
    requirements: []
""")

REQUIREMENTS_SAMD_UTILITY = textwrap.dedent("""\
    metadata:
      project: test_project
      samd_class: utility
    requirements: []
""")

ANOMALY_LOG_EMPTY = textwrap.dedent("""\
    metadata:
      project: test_project
      standard: IEC 62304 §9
    anomalies: []
""")


def _write_requirements(path, content):
    (path / "docs").mkdir(exist_ok=True)
    (path / "docs" / "requirements.yaml").write_text(content)


@pytest.mark.requirement("VER-010")
def test_anomaly_log_present_samd_c_passes(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="check_anomaly_log passes when anomaly_log.yaml present for samd_class C"
    )
    _write_requirements(tmp_path, REQUIREMENTS_SAMD_C)
    (tmp_path / "docs" / "anomaly_log.yaml").write_text(ANOMALY_LOG_EMPTY)

    result = check_anomaly_log(tmp_path)

    assert result["skipped"] is False
    assert result["found"] is True
    assert result["violations"] == []

    report.info("anomaly_log.yaml present, samd_class C → no violations", "VER-010")
    report.auto_save("ver010_anomaly_log_present_samd_c", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-010")
def test_anomaly_log_absent_samd_c_reports_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="check_anomaly_log reports violation when anomaly_log.yaml absent for samd_class C"
    )
    _write_requirements(tmp_path, REQUIREMENTS_SAMD_C)

    result = check_anomaly_log(tmp_path)

    assert result["skipped"] is False
    assert result["found"] is False
    assert len(result["violations"]) >= 1
    assert any("anomaly_log" in v.lower() for v in result["violations"]), (
        f"Violation must mention anomaly_log; got: {result['violations']}"
    )

    report.info(
        f"anomaly_log.yaml absent, samd_class C → violations: {result['violations']}", "VER-010"
    )
    report.auto_save("ver010_anomaly_log_absent_samd_c", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-010")
def test_anomaly_log_absent_samd_b_reports_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="check_anomaly_log reports violation when anomaly_log.yaml absent for samd_class B"
    )
    _write_requirements(tmp_path, REQUIREMENTS_SAMD_B)

    result = check_anomaly_log(tmp_path)

    assert result["skipped"] is False
    assert result["found"] is False
    assert len(result["violations"]) >= 1

    report.info(
        f"anomaly_log.yaml absent, samd_class B → violations: {result['violations']}", "VER-010"
    )
    report.auto_save("ver010_anomaly_log_absent_samd_b", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-010")
def test_anomaly_log_absent_samd_tool_reports_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="check_anomaly_log reports violation when anomaly_log.yaml absent for samd_class tool"
    )
    _write_requirements(tmp_path, REQUIREMENTS_SAMD_TOOL)

    result = check_anomaly_log(tmp_path)

    assert result["skipped"] is False
    assert result["found"] is False
    assert len(result["violations"]) >= 1

    report.info(
        f"anomaly_log.yaml absent, samd_class tool → violations: {result['violations']}", "VER-010"
    )
    report.auto_save("ver010_anomaly_log_absent_samd_tool", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-010")
def test_anomaly_log_absent_utility_is_skipped(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_anomaly_log skips check for samd_class utility")
    _write_requirements(tmp_path, REQUIREMENTS_SAMD_UTILITY)

    result = check_anomaly_log(tmp_path)

    assert result["skipped"] is True
    assert result["violations"] == [], (
        f"utility class must not trigger violations; got: {result['violations']}"
    )

    report.info("samd_class utility → skipped, no violations", "VER-010")
    report.auto_save("ver010_anomaly_log_utility_skipped", evidence_output_dir)
    assert not report.has_errors, report.summary()
