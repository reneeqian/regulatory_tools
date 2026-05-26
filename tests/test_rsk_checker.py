"""Tests for regulatory_tools.quality.rsk_checker."""
import textwrap

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.quality.rsk_checker import check_rsk_requirements


REQUIREMENTS_WITH_RSK = textwrap.dedent("""\
    requirements:
      - id: SYS-001
        title: System req
        description: A system req.
      - id: RSK-001
        type: risk_control
        title: Risk control A
        description: A risk control.
""")

REQUIREMENTS_WITHOUT_RSK = textwrap.dedent("""\
    requirements:
      - id: SYS-001
        title: System req
        description: A system req.
""")

RISK_CONTROLS_YAML = textwrap.dedent("""\
    metadata:
      file_role: risk_controls
      allowed_prefixes: [RSK]
      allowed_types: [risk_control]
    requirements:
      - id: RSK-001
        type: risk_control
        title: Risk control A
        description: A risk control.
        derived_from: [SYS-001]
      - id: RSK-002
        type: risk_control
        title: Risk control B
        description: Another risk control.
        derived_from: [SYS-001]
""")


@pytest.mark.requirement("RSK-001")
def test_rsk_checker_finds_rsk_in_requirements_yaml(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="RSK checker finds RSK- IDs in docs/requirements.yaml")

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "requirements.yaml").write_text(REQUIREMENTS_WITH_RSK)

    result = check_rsk_requirements(tmp_path)

    assert result["found"] is True
    assert "RSK-001" in result["rsk_ids"]

    report.info(f"found=True, rsk_ids={result['rsk_ids']}", "RSK-001")
    report.auto_save("rsk001_checker_finds_in_requirements_yaml", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("RSK-001")
def test_rsk_checker_finds_rsk_in_risk_controls_yaml(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="RSK checker finds RSK- IDs in docs/risk_controls.yaml when requirements.yaml has none"
    )

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "requirements.yaml").write_text(REQUIREMENTS_WITHOUT_RSK)
    (tmp_path / "docs" / "risk_controls.yaml").write_text(RISK_CONTROLS_YAML)

    result = check_rsk_requirements(tmp_path)

    assert result["found"] is True, "RSK IDs in risk_controls.yaml must be discovered"
    assert "RSK-001" in result["rsk_ids"]
    assert "RSK-002" in result["rsk_ids"]

    report.info(f"found=True, rsk_ids={result['rsk_ids']}", "RSK-001")
    report.auto_save("rsk001_checker_finds_in_risk_controls_yaml", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("RSK-001")
def test_rsk_checker_returns_not_found_when_no_docs(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="RSK checker returns found=False when docs/ directory has no requirement files")

    result = check_rsk_requirements(tmp_path)

    assert result["found"] is False
    assert result["rsk_ids"] == []

    report.info("No docs/ directory → found=False, rsk_ids=[]", "RSK-001")
    report.auto_save("rsk001_checker_not_found_no_docs", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("RSK-001")
def test_rsk_checker_deduplicates_ids(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="RSK checker deduplicates RSK- IDs that appear in multiple files")

    (tmp_path / "docs").mkdir()
    # RSK-001 in both files
    (tmp_path / "docs" / "requirements.yaml").write_text(REQUIREMENTS_WITH_RSK)
    (tmp_path / "docs" / "risk_controls.yaml").write_text(RISK_CONTROLS_YAML)

    result = check_rsk_requirements(tmp_path)

    assert result["rsk_ids"].count("RSK-001") == 1, "RSK-001 must appear exactly once despite being in two files"

    report.info(f"rsk_ids={result['rsk_ids']} — no duplicates", "RSK-001")
    report.auto_save("rsk001_checker_deduplicates", evidence_output_dir)
    assert not report.has_errors, report.summary()
