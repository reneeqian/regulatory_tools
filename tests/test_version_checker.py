"""Tests for check_version_baseline() — VER-009.
These tests fail until version_checker.py is implemented.
"""
import textwrap
from unittest.mock import patch

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.quality.version_checker import check_version_baseline


PYPROJECT_VERSION_1_1_0 = textwrap.dedent("""\
    [project]
    name = "regulatory-tools"
    version = "1.1.0"
""")

PYPROJECT_VERSION_0_1_0 = textwrap.dedent("""\
    [project]
    name = "regulatory-tools"
    version = "0.1.0"
""")


@pytest.mark.requirement("VER-009")
def test_version_matches_tag_passes(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_version_baseline passes when pyproject version matches latest git tag")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT_VERSION_1_1_0)

    with patch(
        "regulatory_tools.quality.version_checker._get_latest_tag",
        return_value="v1.1.0",
    ):
        result = check_version_baseline(tmp_path)

    assert result["has_tags"] is True
    assert result["match"] is True
    assert result["pyproject_version"] == "1.1.0"
    assert result["latest_tag"] == "1.1.0"
    assert result["violations"] == []

    report.info("version 1.1.0 matches tag v1.1.0 → no violations", "VER-009")
    report.auto_save("ver009_version_matches_tag", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-009")
def test_version_mismatch_reports_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_version_baseline reports violation when pyproject version != latest tag")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT_VERSION_0_1_0)

    with patch(
        "regulatory_tools.quality.version_checker._get_latest_tag",
        return_value="v1.1.0",
    ):
        result = check_version_baseline(tmp_path)

    assert result["has_tags"] is True
    assert result["match"] is False
    assert result["pyproject_version"] == "0.1.0"
    assert result["latest_tag"] == "1.1.0"
    assert len(result["violations"]) >= 1
    assert any("0.1.0" in v and "1.1.0" in v for v in result["violations"]), (
        f"Violation must mention both versions; got: {result['violations']}"
    )

    report.info(f"version mismatch 0.1.0 vs 1.1.0 → violations: {result['violations']}", "VER-009")
    report.auto_save("ver009_version_mismatch_violation", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-009")
def test_no_git_tags_returns_warning_not_violation(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_version_baseline warns but does not report violation when no git tags exist")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT_VERSION_0_1_0)

    with patch(
        "regulatory_tools.quality.version_checker._get_latest_tag",
        return_value=None,
    ):
        result = check_version_baseline(tmp_path)

    assert result["has_tags"] is False
    assert result["violations"] == [], f"No tags → must not be a violation; got: {result['violations']}"
    assert result["warning"] is not None, "No tags → should set a warning message"

    report.info(f"no git tags → has_tags=False, no violation, warning='{result['warning']}'", "VER-009")
    report.auto_save("ver009_no_tags_warning_only", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("VER-009")
def test_no_pyproject_returns_not_found(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="check_version_baseline returns found=False when pyproject.toml absent")

    with patch(
        "regulatory_tools.quality.version_checker._get_latest_tag",
        return_value="v1.0.0",
    ):
        result = check_version_baseline(tmp_path)

    assert result["found"] is False
    assert result["violations"] == []

    report.info("No pyproject.toml → found=False, no violations", "VER-009")
    report.auto_save("ver009_no_pyproject_not_found", evidence_output_dir)
    assert not report.has_errors, report.summary()
