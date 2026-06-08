"""Tests for regulatory_tools.summary.generator (DOC-005)."""
import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.summary.generator import generate_project_summary  # fails until module exists


# ---------------------------------------------------------------------------
# Inline YAML fixtures — minimal but structurally valid
# ---------------------------------------------------------------------------

_REQUIREMENTS_YAML = textwrap.dedent("""\
    metadata:
      project: TestProject
      samd_class: b
      version: "0.2.0"
    requirements:
      - id: SYS-001
        title: System Requirement One
        description: The system shall do something.
""")

_USER_NEEDS_YAML = textwrap.dedent("""\
    metadata:
      file_role: user_needs
    requirements:
      - id: UN-001
        type: user_need
        title: Clinician needs a fast read
        description: Clinicians need to review results quickly.
        intended_user: Radiologist
        verification_method: T
""")

_SOUP_YAML = textwrap.dedent("""\
    soup:
      - name: numpy
        version: "1.26.4"
        intended_use: Numerical arrays
        license: BSD-3-Clause
        risk: low
        verified_by: unit tests
""")

_HAZARD_YAML = textwrap.dedent("""\
    hazards:
      - id: HAZ-001
        hazard: Missed detection
        cause: Model threshold too low
        effect: Patient harm
        severity: serious
        probability: remote
        mitigation_ref: RSK-001
""")

_ANOMALY_YAML = textwrap.dedent("""\
    metadata:
      project: TestProject
    anomalies: []
""")

_TRACEABILITY_MD = textwrap.dedent("""\
    <!-- AUTO-GENERATED FILE. DO NOT EDIT MANUALLY. -->

    # Requirements Traceability Matrix

    ## Requirement Coverage

    **Coverage:** 100.0% (10 / 10 requirements tested)

    ## Code Coverage

    **Line Coverage:** 88.5%

    ## Forge Code Health

    **Overall Score:** 85.0%  **Grade:** B
""")


def _completed(stdout: str, returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    return m


@pytest.fixture
def full_project_root(tmp_path: Path) -> Path:
    """tmp_path with all docs/ files present."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirements.yaml").write_text(_REQUIREMENTS_YAML)
    (docs / "user_needs.yaml").write_text(_USER_NEEDS_YAML)
    (docs / "soup.yaml").write_text(_SOUP_YAML)
    (docs / "hazard_analysis.yaml").write_text(_HAZARD_YAML)
    (docs / "anomaly_log.yaml").write_text(_ANOMALY_YAML)
    (docs / "traceability_matrix.md").write_text(_TRACEABILITY_MD)
    return tmp_path


_GIT_LOG_OUTPUT = (
    "abc1234 fix(audit): replace anomaly_log.md\n"
    "def5678 fix(audit): add anomaly log\n"
    "ghi9012 feat: add nongated ingestor\n"
    "jkl3456 chore: bump version\n"
)
_GH_ISSUES_OUTPUT = json.dumps([
    {"number": 42, "title": "Add nongated evaluator", "url": "https://github.com/owner/repo/issues/42"},
])


def _fake_subprocess(cmd, **kwargs):
    if cmd[0] == "git" and "log" in cmd:
        return _completed(_GIT_LOG_OUTPUT)
    if cmd[0] == "git" and "remote" in cmd:
        return _completed("https://github.com/owner/repo.git")
    if cmd[0] == "gh":
        return _completed(_GH_ISSUES_OUTPUT)
    return _completed("")


# ---------------------------------------------------------------------------
# Main test: all sections present
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DOC-005")
def test_generate_project_summary_produces_all_sections(full_project_root, evidence_output_dir):
    report = EvidenceReport(
        subject="DOC-005: generate_project_summary produces all required sections"
    )

    with patch("regulatory_tools.summary.generator.generate_traceability_matrix"):
        with patch("regulatory_tools.summary.generator.get_forge_health", return_value=None):
            with patch("subprocess.run", side_effect=_fake_subprocess):
                output_path = generate_project_summary(full_project_root)

    assert output_path.exists(), "must return a path to an existing file"
    content = output_path.read_text()

    for section in (
        "## Forge Health",
        "## SOUP",
        "## Hazards",
        "## Anomalies",
        "## Traceability Coverage",
        "## User Needs",
        "## Recent Commits",
        "## Open Issues",
    ):
        assert section in content, f"Missing section: {section}"
        report.info(f"Section '{section}' found in output", "DOC-005")

    assert "TestProject" in content, "project name from metadata must appear"
    report.info("Project name 'TestProject' found in output", "DOC-005")

    assert "abc1234" in content, "recent commit hash must appear"
    report.info("Recent commit hash found in output", "DOC-005")

    assert "https://github.com/owner/repo/issues/42" in content, "issue URL must appear as hyperlink"
    report.info("Open issue URL found in output", "DOC-005")

    report.auto_save("doc005_project_summary_all_sections", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Graceful fallback: missing optional docs
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DOC-005")
def test_missing_optional_docs_do_not_crash(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DOC-005: generate_project_summary handles missing optional docs without crashing"
    )

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirements.yaml").write_text(_REQUIREMENTS_YAML)
    # hazard_analysis.yaml, soup.yaml, user_needs.yaml, anomaly_log.yaml intentionally absent

    with patch("regulatory_tools.summary.generator.generate_traceability_matrix"):
        with patch("regulatory_tools.summary.generator.get_forge_health", return_value=None):
            with patch("subprocess.run", return_value=_completed("")):
                output_path = generate_project_summary(tmp_path)

    assert output_path.exists()
    content = output_path.read_text()
    assert "## SOUP" in content, "SOUP section must appear even when file is absent"
    assert "## Hazards" in content, "Hazards section must appear even when file is absent"
    report.info("No exception raised with missing optional docs; sections still present", "DOC-005")

    report.auto_save("doc005_missing_docs_graceful", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Graceful fallback: gh not installed
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DOC-005")
def test_gh_not_available_does_not_crash(full_project_root, evidence_output_dir):
    report = EvidenceReport(
        subject="DOC-005: generate_project_summary handles missing gh CLI without crashing"
    )

    def _no_gh(cmd, **kwargs):
        if cmd[0] == "gh":
            raise FileNotFoundError("gh not found")
        if cmd[0] == "git" and "log" in cmd:
            return _completed(_GIT_LOG_OUTPUT)
        return _completed("")

    with patch("regulatory_tools.summary.generator.generate_traceability_matrix"):
        with patch("regulatory_tools.summary.generator.get_forge_health", return_value=None):
            with patch("subprocess.run", side_effect=_no_gh):
                output_path = generate_project_summary(full_project_root)

    assert output_path.exists()
    content = output_path.read_text()
    assert "## Open Issues" in content, "Open Issues section must appear even when gh is unavailable"
    report.info("Open Issues section present even when gh is unavailable", "DOC-005")

    report.auto_save("doc005_gh_not_available", evidence_output_dir)
    assert not report.has_errors, report.summary()
