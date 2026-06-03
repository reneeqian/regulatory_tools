"""
Tests for regulatory_tools.dhf.generators.risk_controls — RiskControlsGenerator (DHF-004).
These tests must fail before RiskControlsGenerator exists.
"""
import textwrap

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.dhf.requirements_reader import RequirementsReader
from regulatory_tools.dhf.generators.risk_controls import RiskControlsGenerator


REQS_WITH_RSK = textwrap.dedent("""
    metadata:
      project: test
      version: 1.0
    requirements:
      - id: SYS-001
        title: System req
        description: A system requirement.
      - id: RSK-001
        type: risk_control
        title: Halt on NaN loss
        description: Training shall halt when loss is non-finite.
        derived_from: [SYS-001]
      - id: RSK-002
        type: risk_control
        title: Partition overlap prevention
        description: Train/test partitions shall not share patients.
        derived_from: [SYS-001]
""")


@pytest.mark.requirement("DHF-004")
def test_risk_controls_generates_rows_for_rsk_requirements(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-004: RiskControlsGenerator produces table rows for all RSK requirements")

    reqs_file = tmp_path / "requirements.yaml"
    reqs_file.write_text(REQS_WITH_RSK)
    reader = RequirementsReader(reqs_file)

    gen = RiskControlsGenerator(reader)
    rows = gen.generate_rows()

    assert "RSK-001" in rows
    assert "Halt on NaN loss" in rows
    assert "RSK-002" in rows
    assert "Partition overlap" in rows

    report.info(f"generate_rows() produced rows for RSK-001 and RSK-002", "DHF-004")
    report.auto_save("dhf004_risk_controls_rows", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-004")
def test_risk_controls_non_rsk_requirements_excluded(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-004: RiskControlsGenerator excludes non-risk-control requirements")

    reqs_file = tmp_path / "requirements.yaml"
    reqs_file.write_text(REQS_WITH_RSK)
    reader = RequirementsReader(reqs_file)

    gen = RiskControlsGenerator(reader)
    rows = gen.generate_rows()

    # SYS-001 may appear in the "Derived From" column — it must not be a row ID (first column)
    assert not any(line.startswith("| SYS-001 ") for line in rows.splitlines())

    report.info("SYS-001 does not appear as a row ID in risk controls output (only in derived_from)", "DHF-004")
    report.auto_save("dhf004_risk_controls_non_rsk_excluded", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-004")
def test_risk_controls_partial_rows_have_manual_fill_markers(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-004: Risk control rows contain manual fill markers for narrative columns")

    reqs_file = tmp_path / "requirements.yaml"
    reqs_file.write_text(REQS_WITH_RSK)
    reader = RequirementsReader(reqs_file)

    gen = RiskControlsGenerator(reader)
    rows = gen.generate_rows()

    # Narrative columns that require manual completion must be marked
    assert "<!-- FILL -->" in rows

    report.info("Rows contain <!-- FILL --> markers for manual completion columns", "DHF-004")
    report.auto_save("dhf004_risk_controls_fill_markers", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-004")
def test_risk_controls_empty_when_no_rsk_requirements(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-004: RiskControlsGenerator returns empty string when no risk_control requirements exist")

    no_rsk = textwrap.dedent("""
        metadata:
          project: test
          version: 1.0
        requirements:
          - id: SYS-001
            title: System req
            description: A system req.
    """)
    reqs_file = tmp_path / "requirements.yaml"
    reqs_file.write_text(no_rsk)

    gen = RiskControlsGenerator(RequirementsReader(reqs_file))
    rows = gen.generate_rows()

    assert rows.strip() == ""

    report.info("No risk_control requirements → generate_rows() returns empty string", "DHF-004")
    report.auto_save("dhf004_risk_controls_empty", evidence_output_dir)
    assert not report.has_errors, report.summary()
