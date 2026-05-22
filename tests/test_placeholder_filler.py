"""
Tests for regulatory_tools.dhf.placeholder_filler — PlaceholderFiller (DHF-002, DHF-006, DHF-010).
These tests must fail before PlaceholderFiller exists.
"""
from pathlib import Path

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.dhf.placeholder_filler import FilledResult, PlaceholderFiller


CONTEXT = {"PROJECT_NAME": "COCA-prj", "AUTHOR": "Renee Qian"}


# ---------------------------------------------------------------------------
# First fill — {{VAR}} → sentinel-wrapped value
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-002")
def test_known_placeholder_is_replaced(evidence_output_dir):
    report = EvidenceReport(subject="DHF-002: PlaceholderFiller replaces known {{VAR}} with the context value")

    filler = PlaceholderFiller(CONTEXT)
    result = filler.fill("Hello {{PROJECT_NAME}}!")

    assert "COCA-prj" in result.content
    assert "{{PROJECT_NAME}}" not in result.content
    assert "PROJECT_NAME" in result.filled

    report.info(f"{{{{PROJECT_NAME}}}} → content contains 'COCA-prj'; filled={result.filled}", "DHF-002")
    report.auto_save("dhf002_known_placeholder_replaced", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-002")
def test_unknown_placeholder_is_left_unchanged(evidence_output_dir):
    report = EvidenceReport(subject="DHF-002: PlaceholderFiller leaves unknown {{VAR}} unchanged and reports it")

    filler = PlaceholderFiller(CONTEXT)
    result = filler.fill("Hello {{UNKNOWN_VAR}}!")

    assert "{{UNKNOWN_VAR}}" in result.content
    assert "UNKNOWN_VAR" in result.unfilled

    report.info(f"{{{{UNKNOWN_VAR}}}} left unchanged; unfilled={result.unfilled}", "DHF-002")
    report.auto_save("dhf002_unknown_placeholder_unchanged", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-010")
def test_filled_value_is_wrapped_in_sentinel_comments(evidence_output_dir):
    report = EvidenceReport(subject="DHF-010: Filled value is wrapped in <!-- DHF_VAR:name --> sentinels")

    filler = PlaceholderFiller(CONTEXT)
    result = filler.fill("Project: {{PROJECT_NAME}}")

    assert "<!-- DHF_VAR:PROJECT_NAME -->" in result.content
    assert "<!-- /DHF_VAR:PROJECT_NAME -->" in result.content
    assert "COCA-prj" in result.content

    report.info(f"Sentinel wrappers present: {result.content!r}", "DHF-010")
    report.auto_save("dhf010_sentinel_wrappers_present", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Second fill — stale sentinel content updated when context changes
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-010")
def test_stale_sentinel_value_updated_on_reraise(evidence_output_dir):
    report = EvidenceReport(subject="DHF-010: Re-fill updates sentinel-wrapped value when context changes")

    filler_v1 = PlaceholderFiller({"PROJECT_NAME": "old-name"})
    first_fill = filler_v1.fill("Project: {{PROJECT_NAME}}")
    assert "old-name" in first_fill.content

    filler_v2 = PlaceholderFiller({"PROJECT_NAME": "new-name"})
    second_fill = filler_v2.fill(first_fill.content)

    assert "new-name" in second_fill.content
    assert "old-name" not in second_fill.content

    report.info(f"After context change: content updated to 'new-name'", "DHF-010")
    report.auto_save("dhf010_stale_sentinel_updated", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-010")
def test_manual_fill_without_sentinel_is_not_overwritten(evidence_output_dir):
    report = EvidenceReport(subject="DHF-010: Manually filled value without sentinel is never touched by the filler")

    # Content that was filled manually (no sentinel wrapper)
    manually_filled = "Project: hand-typed-value"
    filler = PlaceholderFiller({"PROJECT_NAME": "COCA-prj"})
    result = filler.fill(manually_filled)

    # No {{VAR}} patterns and no sentinels → content unchanged
    assert result.content == manually_filled
    assert result.filled == []
    assert result.unfilled == []

    report.info("Content with no {{}} or sentinels passed through unchanged", "DHF-010")
    report.auto_save("dhf010_manual_fill_untouched", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-006")
def test_fill_is_idempotent_when_context_unchanged(evidence_output_dir):
    report = EvidenceReport(subject="DHF-006: Filling the same content twice with same context produces identical output")

    filler = PlaceholderFiller(CONTEXT)
    first = filler.fill("Project: {{PROJECT_NAME}}, author: {{AUTHOR}}")
    second = filler.fill(first.content)

    assert first.content == second.content

    report.info("Two fills with same context produce identical output", "DHF-006")
    report.auto_save("dhf006_fill_idempotent", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# fill_file
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-002")
def test_fill_file_writes_in_place(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-002: fill_file() writes filled content back to the file")

    doc = tmp_path / "doc.md"
    doc.write_text("# {{PROJECT_NAME}}\n\nSome content.")
    filler = PlaceholderFiller(CONTEXT)
    result = filler.fill_file(doc)

    content = doc.read_text()
    assert "COCA-prj" in content
    assert "{{PROJECT_NAME}}" not in content
    assert "PROJECT_NAME" in result.filled

    report.info(f"fill_file wrote sentinel-wrapped value to disk", "DHF-002")
    report.auto_save("dhf002_fill_file_writes_in_place", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-006")
def test_fill_file_does_not_write_when_content_unchanged(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-006: fill_file() skips write when content would not change (avoids spurious diffs)")

    doc = tmp_path / "doc.md"
    doc.write_text("# Static content with no placeholders.")
    original_mtime = doc.stat().st_mtime

    filler = PlaceholderFiller(CONTEXT)
    filler.fill_file(doc)

    assert doc.stat().st_mtime == original_mtime, "File was written even though content did not change"

    report.info("fill_file skipped write — no placeholders, no sentinels to update", "DHF-006")
    report.auto_save("dhf006_fill_file_no_spurious_write", evidence_output_dir)
    assert not report.has_errors, report.summary()
