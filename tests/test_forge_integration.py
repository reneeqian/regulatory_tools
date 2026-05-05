"""Tests for forge_integration: write_forge_health_to_summary and update_readme param."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from regulatory_tools.quality.forge_integration import (
    write_forge_health_to_summary,
    update_readme_forge_health,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_forge_summary():
    return {
        "project_name": "test_proj",
        "grade": "A",
        "overall_score": 0.92,
        "generated_at": "2026-05-04T12:00:00",
        "collectors": {
            "test_metrics": {"score": 0.95, "skipped": False, "skip_reason": None},
            "complexity": {"score": 0.88, "skipped": False, "skip_reason": None},
            "dead_code": {"score": 0.50, "skipped": True, "skip_reason": "no vulture"},
        },
    }


@pytest.fixture
def minimal_forge_summary():
    return {
        "grade": "B",
        "overall_score": 0.80,
        "generated_at": "2026-05-01T08:00:00",
        "collectors": {},
    }


# ---------------------------------------------------------------------------
# write_forge_health_to_summary — writes to $GITHUB_STEP_SUMMARY
# ---------------------------------------------------------------------------

@pytest.mark.requirement("VER-004")
@pytest.mark.requirement("INF-003")
def test_write_forge_health_to_summary_writes_to_step_summary(tmp_path, monkeypatch, sample_forge_summary):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_forge_health_to_summary(sample_forge_summary)

    content = summary_file.read_text()
    assert "## Forge Health" in content
    assert "Grade: A" in content
    assert "0.92" in content
    assert "Test Metrics" in content
    assert "Complexity" in content


@pytest.mark.requirement("VER-004")
def test_write_forge_health_to_summary_skips_skipped_collectors(tmp_path, monkeypatch, sample_forge_summary):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_forge_health_to_summary(sample_forge_summary)

    content = summary_file.read_text()
    assert "Dead Code" not in content


@pytest.mark.requirement("VER-004")
def test_write_forge_health_to_summary_stdout_fallback(capsys, monkeypatch, sample_forge_summary):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    write_forge_health_to_summary(sample_forge_summary)

    captured = capsys.readouterr()
    assert "Grade: A" in captured.out
    assert "0.92" in captured.out


@pytest.mark.requirement("VER-004")
def test_write_forge_health_to_summary_empty_collectors(capsys, monkeypatch, minimal_forge_summary):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    write_forge_health_to_summary(minimal_forge_summary)

    captured = capsys.readouterr()
    assert "Grade: B" in captured.out
    assert "0.80" in captured.out


@pytest.mark.requirement("VER-004")
def test_write_forge_health_to_summary_none_score(capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    summary = {
        "grade": "C",
        "overall_score": None,
        "generated_at": "2026-05-01T00:00:00",
        "collectors": {
            "test_metrics": {"score": None, "skipped": False, "skip_reason": None},
        },
    }

    write_forge_health_to_summary(summary)

    captured = capsys.readouterr()
    assert "N/A" in captured.out


# ---------------------------------------------------------------------------
# run_tests_and_trace — update_readme=False routes to write_forge_health_to_summary
# ---------------------------------------------------------------------------

@pytest.mark.requirement("VER-004")
@pytest.mark.requirement("SYS-002")
def test_run_tests_and_trace_update_readme_false_calls_summary(tmp_path, monkeypatch):
    """update_readme=False should call write_forge_health_to_summary, not update_readme_forge_health."""
    from regulatory_tools.testing.run_tests_and_trace import run_tests_and_trace

    fake_summary = {
        "grade": "B", "overall_score": 0.80,
        "generated_at": "2026-05-01T00:00:00", "collectors": {},
    }

    with patch("regulatory_tools.testing.run_tests_and_trace.run_pytest_with_coverage"), \
         patch("regulatory_tools.testing.run_tests_and_trace._run_quality_checks"), \
         patch("regulatory_tools.testing.run_tests_and_trace.generate_traceability_matrix", return_value=fake_summary), \
         patch("regulatory_tools.quality.forge_integration.write_forge_health_to_summary") as mock_summary, \
         patch("regulatory_tools.quality.forge_integration.update_readme_forge_health") as mock_readme:

        run_tests_and_trace(tmp_path, min_grade=None, update_readme=False)

    mock_summary.assert_called_once_with(fake_summary)
    mock_readme.assert_not_called()


@pytest.mark.requirement("VER-004")
@pytest.mark.requirement("SYS-002")
def test_run_tests_and_trace_update_readme_true_calls_readme(tmp_path, monkeypatch):
    """update_readme=True (default) should call update_readme_forge_health."""
    from regulatory_tools.testing.run_tests_and_trace import run_tests_and_trace

    fake_summary = {
        "grade": "B", "overall_score": 0.80,
        "generated_at": "2026-05-01T00:00:00", "collectors": {},
    }

    with patch("regulatory_tools.testing.run_tests_and_trace.run_pytest_with_coverage"), \
         patch("regulatory_tools.testing.run_tests_and_trace._run_quality_checks"), \
         patch("regulatory_tools.testing.run_tests_and_trace.generate_traceability_matrix", return_value=fake_summary), \
         patch("regulatory_tools.quality.forge_integration.update_readme_forge_health") as mock_readme, \
         patch("regulatory_tools.quality.forge_integration.write_forge_health_to_summary") as mock_summary:

        run_tests_and_trace(tmp_path, min_grade=None, update_readme=True)

    mock_readme.assert_called_once_with(tmp_path, fake_summary)
    mock_summary.assert_not_called()


# ---------------------------------------------------------------------------
# update_readme_forge_health — regression: still writes markers correctly
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DOC-002")
def test_update_readme_forge_health_replaces_markers(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Project\n\n"
        "<!-- forge-health-start -->\n"
        "old content\n"
        "<!-- forge-health-end -->\n"
    )
    summary = {
        "grade": "A",
        "overall_score": 0.91,
        "generated_at": "2026-05-04T00:00:00",
        "collectors": {
            "test_metrics": {"score": 0.95, "skipped": False, "skip_reason": None},
        },
    }

    update_readme_forge_health(tmp_path, summary)

    content = readme.read_text()
    assert "old content" not in content
    assert "Grade: A" in content
    assert "<!-- forge-health-start -->" in content
    assert "<!-- forge-health-end -->" in content


@pytest.mark.requirement("DOC-002")
def test_update_readme_forge_health_appends_when_no_markers(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n\nSome content.\n")
    summary = {
        "grade": "B",
        "overall_score": 0.80,
        "generated_at": "2026-05-01T00:00:00",
        "collectors": {},
    }

    update_readme_forge_health(tmp_path, summary)

    content = readme.read_text()
    assert "## Forge Health" in content
    assert "<!-- forge-health-start -->" in content


@pytest.mark.requirement("DOC-002")
def test_update_readme_forge_health_no_readme_is_noop(tmp_path):
    summary = {"grade": "A", "overall_score": 0.9, "generated_at": "2026-05-01T00:00:00", "collectors": {}}
    update_readme_forge_health(tmp_path, summary)
    assert not (tmp_path / "README.md").exists()
