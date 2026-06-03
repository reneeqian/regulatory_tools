"""Tests for regulatory_tools.dhf.impact_analyzer (DHF-015)."""
from __future__ import annotations

import subprocess
import sys

import pytest

from regulatory_tools.dhf.impact_analyzer import DHFImpactAnalyzer


@pytest.mark.requirement("DHF-015")
def test_requirements_change_triggers_auto_section():
    """Changing docs/requirements.yaml produces an auto section for system_requirements.md."""
    analyzer = DHFImpactAnalyzer()
    report = analyzer.analyze(["docs/requirements.yaml"])
    assert any("system_requirements" in s.dhf_file for s in report.auto_sections)


@pytest.mark.requirement("DHF-015")
def test_risk_controls_change_triggers_manual_section():
    """Changing docs/risk_controls.yaml produces a manual section for risk_control_measures.md."""
    analyzer = DHFImpactAnalyzer()
    report = analyzer.analyze(["docs/risk_controls.yaml"])
    assert any("risk_control_measures" in s.dhf_file for s in report.manual_sections)


@pytest.mark.requirement("DHF-015")
def test_source_change_triggers_sdp_manual_review():
    """Changing any src/ file produces a manual section for sdp.md."""
    analyzer = DHFImpactAnalyzer()
    report = analyzer.analyze(["src/coronary_prj/ingestors/base_ingestor.py"])
    assert any("sdp" in s.dhf_file for s in report.manual_sections)


@pytest.mark.requirement("DHF-015")
def test_no_changed_files_returns_empty_report():
    """Empty changed-file list produces an empty impact report."""
    analyzer = DHFImpactAnalyzer()
    report = analyzer.analyze([])
    assert report.auto_sections == []
    assert report.manual_sections == []


@pytest.mark.requirement("DHF-015")
def test_cli_entry_point_exits_zero():
    """CLI exits 0 and prints the DHF impact summary including generate_dhf.py instruction."""
    result = subprocess.run(
        [sys.executable, "-m", "regulatory_tools.dhf.impact_analyzer",
         "--changed", "docs/requirements.yaml"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "DHF Impact Summary" in result.stdout
    assert "generate_dhf.py" in result.stdout
    assert "system_requirements" in result.stdout
