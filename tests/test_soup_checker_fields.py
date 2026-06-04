"""Tests for check_soup_fields() — VER-008.
These tests fail until check_soup_fields() is implemented in soup_checker.py.
"""
import textwrap

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.quality.soup_checker import check_soup_fields


SOUP_COMPLETE = textwrap.dedent("""\
    soup:
      - name: pyyaml
        version: "6.0.3"
        intended_use: "Parsing YAML configuration files"
        license: MIT
        risk: low
        verified_by: pip-audit
""")

SOUP_USES_PURPOSE = textwrap.dedent("""\
    soup:
      - name: pyyaml
        version: "6.0.3"
        purpose: "Parsing YAML configuration files"
        license: MIT
        risk: low
        verified_by: pip-audit
""")

SOUP_MISSING_RISK = textwrap.dedent("""\
    soup:
      - name: pyyaml
        version: "6.0.3"
        intended_use: "Parsing YAML configuration files"
        license: MIT
        verified_by: pip-audit
""")

SOUP_MISSING_VERIFIED_BY = textwrap.dedent("""\
    soup:
      - name: pyyaml
        version: "6.0.3"
        intended_use: "Parsing YAML configuration files"
        license: MIT
        risk: low
""")

SOUP_MISSING_INTENDED_USE = textwrap.dedent("""\
    soup:
      - name: pyyaml
        version: "6.0.3"
        license: MIT
        risk: low
        verified_by: pip-audit
""")

SOUP_MULTIPLE_ENTRIES_ONE_BAD = textwrap.dedent("""\
    soup:
      - name: pyyaml
        version: "6.0.3"
        intended_use: "Parsing YAML"
        license: MIT
        risk: low
        verified_by: pip-audit
      - name: torch
        version: "2.0.0"
        purpose: "Deep learning"
        license: BSD-3-Clause
        risk: high
        verified_by: pip-audit
""")


@pytest.mark.requirement("VER-008")
def test_soup_fields_fully_populated_entry_passes(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_soup_fields passes when all required fields are present")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "soup.yaml").write_text(SOUP_COMPLETE)

    result = check_soup_fields(tmp_path)

    assert result["found"] is True
    assert result["violations"] == [], f"Expected no violations, got: {result['violations']}"

    report.info("Complete SOUP entry → no violations", "VER-008")
    report.auto_save("ver008_soup_fields_complete_passes", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-008")
def test_soup_fields_purpose_triggers_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_soup_fields reports violation when entry uses 'purpose' instead of 'intended_use'")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "soup.yaml").write_text(SOUP_USES_PURPOSE)

    result = check_soup_fields(tmp_path)

    assert result["found"] is True
    assert any("purpose" in v.lower() or "intended_use" in v.lower() for v in result["violations"]), (
        f"Expected a violation about 'purpose'/'intended_use', got: {result['violations']}"
    )

    report.info(f"'purpose' field name → violation: {result['violations']}", "VER-008")
    report.auto_save("ver008_soup_fields_purpose_violation", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-008")
def test_soup_fields_missing_risk_triggers_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_soup_fields reports violation when 'risk' field is absent")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "soup.yaml").write_text(SOUP_MISSING_RISK)

    result = check_soup_fields(tmp_path)

    assert result["found"] is True
    assert any("risk" in v.lower() for v in result["violations"]), (
        f"Expected a violation about missing 'risk', got: {result['violations']}"
    )

    report.info(f"Missing 'risk' → violation: {result['violations']}", "VER-008")
    report.auto_save("ver008_soup_fields_missing_risk", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-008")
def test_soup_fields_missing_verified_by_triggers_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_soup_fields reports violation when 'verified_by' field is absent")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "soup.yaml").write_text(SOUP_MISSING_VERIFIED_BY)

    result = check_soup_fields(tmp_path)

    assert result["found"] is True
    assert any("verified_by" in v.lower() for v in result["violations"]), (
        f"Expected a violation about missing 'verified_by', got: {result['violations']}"
    )

    report.info(f"Missing 'verified_by' → violation: {result['violations']}", "VER-008")
    report.auto_save("ver008_soup_fields_missing_verified_by", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-008")
def test_soup_fields_missing_intended_use_triggers_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_soup_fields reports violation when 'intended_use' field is absent")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "soup.yaml").write_text(SOUP_MISSING_INTENDED_USE)

    result = check_soup_fields(tmp_path)

    assert result["found"] is True
    assert any("intended_use" in v.lower() for v in result["violations"]), (
        f"Expected a violation about missing 'intended_use', got: {result['violations']}"
    )

    report.info(f"Missing 'intended_use' → violation: {result['violations']}", "VER-008")
    report.auto_save("ver008_soup_fields_missing_intended_use", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-008")
def test_soup_fields_absent_soup_yaml_returns_not_found(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_soup_fields returns found=False when docs/soup.yaml absent")

    result = check_soup_fields(tmp_path)

    assert result["found"] is False
    assert result["violations"] == []

    report.info("No soup.yaml → found=False, no violations", "VER-008")
    report.auto_save("ver008_soup_fields_absent_file", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-008")
def test_soup_fields_violation_per_entry(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_soup_fields reports violations per individual entry")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "soup.yaml").write_text(SOUP_MULTIPLE_ENTRIES_ONE_BAD)

    result = check_soup_fields(tmp_path)

    assert result["found"] is True
    assert len(result["violations"]) >= 1, "torch entry with 'purpose' must generate at least one violation"
    assert not any("pyyaml" in v for v in result["violations"]), (
        "pyyaml entry is fully populated; must not appear in violations"
    )

    report.info(f"1 bad entry out of 2 → {len(result['violations'])} violation(s)", "VER-008")
    report.auto_save("ver008_soup_fields_per_entry_violation", evidence_output_dir)
    assert not report.has_errors, report.summary()
