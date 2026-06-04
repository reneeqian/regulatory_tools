"""Tests for regulatory_tools.dhf.impact_analyzer (DHF-015)."""
from __future__ import annotations

import subprocess
import sys

import pytest

from regulatory_tools.dhf.impact_analyzer import DHFImpactAnalyzer
from regulatory_tools.evidence.evidence_report import EvidenceReport


@pytest.mark.requirement("DHF-015")
def test_requirements_change_triggers_auto_section(evidence_output_dir):
    """Changing docs/requirements.yaml produces an auto section for system_requirements.md."""
    report = EvidenceReport(subject="DHFImpactAnalyzer: requirements.yaml change triggers auto section")
    analyzer = DHFImpactAnalyzer()
    result = analyzer.analyze(["docs/requirements.yaml"])
    auto_files = [s.dhf_file for s in result.auto_sections]
    report.info(f"auto_sections={auto_files}", "DHF-015")
    report.auto_save("dhf015_requirements_change_triggers_auto_section", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert any("system_requirements" in s.dhf_file for s in result.auto_sections)


@pytest.mark.requirement("DHF-015")
def test_risk_controls_change_triggers_manual_section(evidence_output_dir):
    """Changing docs/risk_controls.yaml produces a manual section for risk_control_measures.md."""
    report = EvidenceReport(subject="DHFImpactAnalyzer: risk_controls.yaml change triggers manual section")
    analyzer = DHFImpactAnalyzer()
    result = analyzer.analyze(["docs/risk_controls.yaml"])
    manual_files = [s.dhf_file for s in result.manual_sections]
    report.info(f"manual_sections={manual_files}", "DHF-015")
    report.auto_save("dhf015_risk_controls_change_triggers_manual_section", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert any("risk_control_measures" in s.dhf_file for s in result.manual_sections)


@pytest.mark.requirement("DHF-015")
def test_source_change_triggers_sdp_manual_review(evidence_output_dir):
    """Changing any src/ file produces a manual section for sdp.md."""
    report = EvidenceReport(subject="DHFImpactAnalyzer: src/ change triggers sdp.md manual review")
    analyzer = DHFImpactAnalyzer()
    result = analyzer.analyze(["src/coronary_prj/ingestors/base_ingestor.py"])
    manual_files = [s.dhf_file for s in result.manual_sections]
    report.info(f"manual_sections={manual_files}", "DHF-015")
    report.auto_save("dhf015_source_change_triggers_sdp_manual_review", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert any("sdp" in s.dhf_file for s in result.manual_sections)


@pytest.mark.requirement("DHF-015")
def test_no_changed_files_returns_empty_report(evidence_output_dir):
    """Empty changed-file list produces an empty impact report."""
    report = EvidenceReport(subject="DHFImpactAnalyzer: empty input produces empty report")
    analyzer = DHFImpactAnalyzer()
    result = analyzer.analyze([])
    report.info(
        f"auto_sections={result.auto_sections}, manual_sections={result.manual_sections}",
        "DHF-015",
    )
    report.auto_save("dhf015_no_changed_files_returns_empty_report", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert result.auto_sections == []
    assert result.manual_sections == []


@pytest.mark.requirement("DHF-015")
def test_cli_entry_point_exits_zero(evidence_output_dir):
    """CLI exits 0 and prints the DHF impact summary including generate_dhf.py instruction."""
    report = EvidenceReport(subject="DHFImpactAnalyzer CLI: exits 0 and prints structured summary")
    result = subprocess.run(
        [sys.executable, "-m", "regulatory_tools.dhf.impact_analyzer",
         "--changed", "docs/requirements.yaml"],
        capture_output=True,
        text=True,
    )
    report.info(
        f"returncode={result.returncode}, stdout_contains_summary={'DHF Impact Summary' in result.stdout}",
        "DHF-015",
    )
    report.auto_save("dhf015_cli_entry_point_exits_zero", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert result.returncode == 0
    assert "DHF Impact Summary" in result.stdout
    assert "generate_dhf.py" in result.stdout
    assert "system_requirements" in result.stdout
