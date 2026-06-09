"""Tests for check_linked_requirements() — VER-011.
These tests fail until linked_checker.py is implemented.
"""

import textwrap

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.quality.linked_checker import check_linked_requirements

REQUIREMENTS_SAMD_C = textwrap.dedent("""\
    metadata:
      project: test_project
      samd_class: C
    requirements: []
""")

REQUIREMENTS_UTILITY = textwrap.dedent("""\
    metadata:
      project: test_project
      samd_class: utility
    requirements: []
""")

RTM_NO_LINKED = textwrap.dedent("""\
    # Requirements Traceability Matrix
    | Requirement ID | Source | Title | Linked Tests | Evidence Artifacts | Status |
    |---|---|---|---|---|---|
    | SYS-001 | requirements | Some requirement | tests/test_foo.py::test_bar | foo.json | PASS |
    | DAT-001 | requirements | Another requirement | tests/test_baz.py::test_qux | baz.json | PASS |
""")

RTM_WITH_LINKED = textwrap.dedent("""\
    # Requirements Traceability Matrix
    | Requirement ID | Source | Title | Linked Tests | Evidence Artifacts | Status |
    |---|---|---|---|---|---|
    | SYS-001 | requirements | Some requirement | tests/test_foo.py::test_bar | foo.json | PASS |
    | VER-005 | requirements | Traceability generation | tests/test_trace.py::test_gen |  | LINKED |
    | INF-002 | requirements | Config validation | tests/test_cfg.py::test_val |  | LINKED |
""")

RTM_ALL_UNTESTED = textwrap.dedent("""\
    # Requirements Traceability Matrix
    | Requirement ID | Source | Title | Linked Tests | Evidence Artifacts | Status |
    |---|---|---|---|---|---|
    | SYS-001 | requirements | Some requirement |  |  | UNTESTED |
""")


def _write_setup(path, requirements_content, rtm_content):
    (path / "docs").mkdir(exist_ok=True)
    (path / "docs" / "requirements.yaml").write_text(requirements_content)
    (path / "docs" / "traceability_matrix.md").write_text(rtm_content)


@pytest.mark.requirement("VER-011")
def test_no_linked_rows_passes(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_linked_requirements passes when no LINKED rows in RTM")
    _write_setup(tmp_path, REQUIREMENTS_SAMD_C, RTM_NO_LINKED)

    result = check_linked_requirements(tmp_path)

    assert result["skipped"] is False
    assert result["linked_ids"] == [], f"Expected no LINKED IDs; got: {result['linked_ids']}"

    report.info("0 LINKED rows, samd_class C → passes", "VER-011")
    report.auto_save("ver011_no_linked_rows_passes", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-011")
def test_linked_rows_samd_c_reports_ids(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="check_linked_requirements returns LINKED requirement IDs for samd_class C"
    )
    _write_setup(tmp_path, REQUIREMENTS_SAMD_C, RTM_WITH_LINKED)

    result = check_linked_requirements(tmp_path)

    assert result["skipped"] is False
    assert "VER-005" in result["linked_ids"]
    assert "INF-002" in result["linked_ids"]
    assert len(result["linked_ids"]) == 2

    report.info(f"2 LINKED rows, samd_class C → linked_ids={result['linked_ids']}", "VER-011")
    report.auto_save("ver011_linked_rows_samd_c_ids", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-011")
def test_linked_rows_utility_is_skipped(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="check_linked_requirements skips check for samd_class utility even with LINKED rows"
    )
    _write_setup(tmp_path, REQUIREMENTS_UTILITY, RTM_WITH_LINKED)

    result = check_linked_requirements(tmp_path)

    assert result["skipped"] is True
    assert result["linked_ids"] == [], (
        f"utility class must not return LINKED IDs; got: {result['linked_ids']}"
    )

    report.info("samd_class utility → skipped regardless of LINKED rows", "VER-011")
    report.auto_save("ver011_linked_utility_skipped", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-011")
def test_untested_rows_not_counted_as_linked(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="check_linked_requirements does not count UNTESTED rows as LINKED"
    )
    _write_setup(tmp_path, REQUIREMENTS_SAMD_C, RTM_ALL_UNTESTED)

    result = check_linked_requirements(tmp_path)

    assert result["skipped"] is False
    assert result["linked_ids"] == [], (
        f"UNTESTED rows must not be counted as LINKED; got: {result['linked_ids']}"
    )

    report.info("UNTESTED rows only → linked_ids=[]", "VER-011")
    report.auto_save("ver011_untested_not_linked", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-011")
def test_no_rtm_returns_empty(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="check_linked_requirements returns empty list when traceability_matrix.md absent"
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "requirements.yaml").write_text(REQUIREMENTS_SAMD_C)

    result = check_linked_requirements(tmp_path)

    assert result["linked_ids"] == []

    report.info("No RTM file → linked_ids=[]", "VER-011")
    report.auto_save("ver011_no_rtm_empty", evidence_output_dir)
    assert not report.has_errors, report.summary()
