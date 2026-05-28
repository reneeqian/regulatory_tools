"""
Tests for regulatory_tools.dhf.section_scaffolder — SectionScaffolder (DHF-005).
These tests must fail before SectionScaffolder exists.
"""
from pathlib import Path

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.dhf.placeholder_filler import PlaceholderFiller
from regulatory_tools.dhf.section_scaffolder import SectionScaffolder


def _make_templates(tmp_path: Path) -> Path:
    """Create a minimal templates directory with sections 10 and 11."""
    templates = tmp_path / "templates"
    (templates / "10_software_development_plan").mkdir(parents=True)
    (templates / "10_software_development_plan" / "sdp.md").write_text(
        "# SDP — {{PROJECT_NAME}}\n\nContent here.\n"
    )
    (templates / "11_anomaly_log").mkdir()
    (templates / "11_anomaly_log" / "anomaly_log.md").write_text(
        "# Anomaly Log — {{PROJECT_NAME}}\n\n| ID | Description |\n"
    )
    return templates


@pytest.mark.requirement("DHF-005")
def test_scaffolder_copies_missing_sections(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-005: SectionScaffolder copies missing template sections into dhf_root")

    templates = _make_templates(tmp_path)
    dhf_root = tmp_path / "dhf"
    dhf_root.mkdir()

    filler = PlaceholderFiller({"PROJECT_NAME": "COCA-prj"})
    scaffolder = SectionScaffolder(templates, dhf_root, filler)
    created = scaffolder.scaffold_missing()

    assert len(created) == 2
    assert (dhf_root / "10_software_development_plan" / "sdp.md").exists()
    assert (dhf_root / "11_anomaly_log" / "anomaly_log.md").exists()

    report.info(f"scaffold_missing() created {len(created)} files: {[str(p) for p in created]}", "DHF-005")
    report.auto_save("dhf005_scaffolder_copies_missing", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-005")
def test_scaffolder_fills_placeholders_in_copied_files(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-005: SectionScaffolder runs PlaceholderFiller on copied files")

    templates = _make_templates(tmp_path)
    dhf_root = tmp_path / "dhf"
    dhf_root.mkdir()

    filler = PlaceholderFiller({"PROJECT_NAME": "COCA-prj"})
    SectionScaffolder(templates, dhf_root, filler).scaffold_missing()

    content = (dhf_root / "10_software_development_plan" / "sdp.md").read_text()
    assert "COCA-prj" in content
    assert "{{PROJECT_NAME}}" not in content

    report.info("Copied sdp.md has {{PROJECT_NAME}} filled with 'COCA-prj'", "DHF-005")
    report.auto_save("dhf005_scaffolder_fills_placeholders", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-005")
def test_scaffolder_does_not_overwrite_existing_sections(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-005: SectionScaffolder leaves existing DHF sections untouched")

    templates = _make_templates(tmp_path)
    dhf_root = tmp_path / "dhf"
    (dhf_root / "10_software_development_plan").mkdir(parents=True)
    existing = dhf_root / "10_software_development_plan" / "sdp.md"
    existing.write_text("# Existing content — do not overwrite\n")

    filler = PlaceholderFiller({"PROJECT_NAME": "COCA-prj"})
    created = SectionScaffolder(templates, dhf_root, filler).scaffold_missing()

    # Only section 11 should be scaffolded
    created_names = [p.name for p in created]
    assert "sdp.md" not in created_names
    assert existing.read_text() == "# Existing content — do not overwrite\n"

    report.info(f"Existing sdp.md untouched; only {created_names} were created", "DHF-005")
    report.auto_save("dhf005_scaffolder_no_overwrite", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-005")
def test_scaffolder_returns_empty_when_all_sections_exist(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-005: SectionScaffolder returns [] when all template sections already exist in dhf_root")

    templates = _make_templates(tmp_path)
    dhf_root = tmp_path / "dhf"
    # Pre-create both sections
    for section_dir in templates.iterdir():
        (dhf_root / section_dir.name).mkdir(parents=True)
        for f in section_dir.iterdir():
            (dhf_root / section_dir.name / f.name).write_text("existing")

    filler = PlaceholderFiller({"PROJECT_NAME": "COCA-prj"})
    created = SectionScaffolder(templates, dhf_root, filler).scaffold_missing()

    assert created == []

    report.info("All sections exist → scaffold_missing() returned []", "DHF-005")
    report.auto_save("dhf005_scaffolder_empty_when_all_exist", evidence_output_dir)
    assert not report.has_errors, report.summary()
