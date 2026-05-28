"""
Integration tests for regulatory_tools.dhf.generator — DHFGenerator (DHF-006, DHF-009).
These tests must fail before DHFGenerator exists.
"""
import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.dhf.generator import DHFGenerator, DHFGenerationReport
from regulatory_tools.dhf.validator import DHFValidationError


def _mock_proc(stdout: str) -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = 0
    return m


# ---------------------------------------------------------------------------
# Helpers — build a minimal but valid synthetic DHF tree
# ---------------------------------------------------------------------------

SOUP_YAML = textwrap.dedent("""
    soup:
      - name: numpy
        version: "2.1.0"
        purpose: Arrays
        license: BSD-3-Clause
""")

REQUIREMENTS_YAML = textwrap.dedent("""
    metadata:
      project: test
      version: 1.0
    requirements:
      - id: SYS-001
        title: System req
        description: A system req.
      - id: RSK-001
        type: risk_control
        title: Risk control
        description: A risk control.
        derived_from: [SYS-001]
""")

TRACEABILITY_MD = textwrap.dedent("""
    # Traceability Matrix
    **Coverage:** 100.0% (2 / 2 requirements tested)
    **Overall Score:** 95.0%  **Grade:** A
""")

CONTEXT_TEMPLATE = textwrap.dedent("""
    project_name: "COCA-prj"
    responsible_person: "Renee Qian"
    code_repos: ["Coronary_prj"]
    author: "Renee Qian"
    data_sources:
      soup: "{soup}"
      evidence_runs: "{evidence_runs}"
      requirements: "{requirements}"
      traceability_matrix: "{traceability_matrix}"
    templates_root: "{templates_root}"
    git_repo: "{git_repo}"
""")


def _make_dhf_tree(tmp_path: Path) -> tuple[Path, Path]:
    """Returns (dhf_root, context_path)."""
    # Data sources
    soup = tmp_path / "data" / "soup.yaml"
    soup.parent.mkdir()
    soup.write_text(SOUP_YAML)

    reqs = tmp_path / "data" / "requirements.yaml"
    reqs.write_text(REQUIREMENTS_YAML)

    evidence_runs = tmp_path / "data" / "evidence_runs"
    evidence_runs.mkdir()
    run_dir = evidence_runs / "20260501_120000"
    run_dir.mkdir()
    (run_dir / "test_abc.json").write_text(json.dumps({
        "test_id": "test_abc", "subject": "Test ABC", "result": "PASS",
        "requirement_tags": ["SYS-001"], "requirements": [], "issues": [],
        "timestamp": "2026-05-01T12:00:00",
    }))

    traceability = tmp_path / "data" / "traceability_matrix.md"
    traceability.write_text(TRACEABILITY_MD)

    git_repo = tmp_path / "repo"
    git_repo.mkdir()

    # Templates root with one missing section
    templates = tmp_path / "templates"
    (templates / "10_software_development_plan").mkdir(parents=True)
    (templates / "10_software_development_plan" / "sdp.md").write_text(
        "# SDP — {{PROJECT_NAME}}\n"
    )

    # DHF root — has existing section 05 but not 10
    dhf_root = tmp_path / "dhf"
    (dhf_root / "05_soup").mkdir(parents=True)
    (dhf_root / "05_soup" / "soup_register.md").write_text(
        "# SOUP Register\n\n"
        "<!-- DHF_SOUP_TABLE_START -->\n"
        "<!-- DHF_SOUP_TABLE_END -->\n"
    )

    ctx_path = tmp_path / "dhf_context.yaml"
    ctx_path.write_text(CONTEXT_TEMPLATE.format(
        soup=soup, evidence_runs=evidence_runs,
        requirements=reqs, traceability_matrix=traceability,
        templates_root=templates, git_repo=git_repo,
    ))

    return dhf_root, ctx_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-006")
def test_generator_run_all_fills_placeholders(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-006: DHFGenerator.run_all() fills placeholders in existing DHF documents")

    dhf_root, ctx_path = _make_dhf_tree(tmp_path)
    # Add a doc with a placeholder
    (dhf_root / "README.md").write_text("# {{PROJECT_NAME}} DHF\n")

    gen = DHFGenerator.from_config(dhf_root=dhf_root, context_file=ctx_path)
    result = gen.run_all()

    content = (dhf_root / "README.md").read_text()
    assert "COCA-prj" in content
    assert "{{PROJECT_NAME}}" not in content
    assert isinstance(result, DHFGenerationReport)

    report.info("run_all() filled {{PROJECT_NAME}} in README.md", "DHF-006")
    report.auto_save("dhf006_generator_fills_placeholders", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-006")
def test_generator_run_all_updates_soup_register(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-006: DHFGenerator.run_all() updates SOUP register sentinel section")

    dhf_root, ctx_path = _make_dhf_tree(tmp_path)
    gen = DHFGenerator.from_config(dhf_root=dhf_root, context_file=ctx_path)
    gen.run_all()

    content = (dhf_root / "05_soup" / "soup_register.md").read_text()
    assert "numpy" in content

    report.info("run_all() populated SOUP register with numpy entry", "DHF-006")
    report.auto_save("dhf006_generator_updates_soup", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-005")
def test_generator_run_all_scaffolds_missing_sections(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-005: DHFGenerator.run_all() scaffolds section 10 which is missing from dhf_root")

    dhf_root, ctx_path = _make_dhf_tree(tmp_path)
    gen = DHFGenerator.from_config(dhf_root=dhf_root, context_file=ctx_path)
    result = gen.run_all()

    sdp = dhf_root / "10_software_development_plan" / "sdp.md"
    assert sdp.exists()
    assert "COCA-prj" in sdp.read_text()
    assert len(result.scaffolded_sections) >= 1

    report.info(f"section 10 scaffolded; sdp.md contains 'COCA-prj'", "DHF-005")
    report.auto_save("dhf005_generator_scaffolds_missing", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-006")
def test_generator_run_all_is_idempotent(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-006: DHFGenerator.run_all() twice produces no diff on second run")

    dhf_root, ctx_path = _make_dhf_tree(tmp_path)
    gen = DHFGenerator.from_config(dhf_root=dhf_root, context_file=ctx_path)
    gen.run_all()

    # Snapshot all file contents after first run
    snapshots = {
        p: p.read_text()
        for p in sorted(dhf_root.rglob("*.md"))
    }

    gen.run_all()

    for path, original in snapshots.items():
        assert path.read_text() == original, f"Second run changed {path.name}"

    report.info(f"Second run_all() produced no changes across {len(snapshots)} files", "DHF-006")
    report.auto_save("dhf006_generator_idempotent", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-009")
def test_generator_raises_on_invalid_context(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-009: DHFGenerator.from_config raises DHFValidationError when context is invalid")

    dhf_root = tmp_path / "dhf"
    dhf_root.mkdir()
    bad_ctx = tmp_path / "dhf_context.yaml"
    bad_ctx.write_text("project_name: 'COCA-prj'\n# missing all other required fields\n")

    with pytest.raises(DHFValidationError):
        DHFGenerator.from_config(dhf_root=dhf_root, context_file=bad_ctx)

    report.info("DHFGenerator.from_config raised DHFValidationError on incomplete context", "DHF-009")
    report.auto_save("dhf009_generator_raises_on_invalid_context", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-003")
def test_generator_run_all_updates_baseline_register(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-003: DHFGenerator.run_all() populates BASELINE_REGISTER sentinel section when git tags exist"
    )

    dhf_root, ctx_path = _make_dhf_tree(tmp_path)
    (dhf_root / "07_cm").mkdir()
    baseline_doc = dhf_root / "07_cm" / "baseline_register.md"
    baseline_doc.write_text(
        "# Baseline Register\n\n"
        "<!-- DHF_BASELINE_REGISTER_START -->\n"
        "<!-- DHF_BASELINE_REGISTER_END -->\n"
    )

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_proc("v1.0.0\n"),
            _mock_proc("abc1234def56\n"),
            _mock_proc("2026-05-01 10:00:00 +0000\n"),
        ]
        gen = DHFGenerator.from_config(dhf_root=dhf_root, context_file=ctx_path)
        gen.run_all()

    content = baseline_doc.read_text()
    assert "v1.0.0" in content
    assert "abc1234" in content

    report.info("run_all() populated BASELINE_REGISTER sentinel section with v1.0.0 tag", "DHF-003")
    report.auto_save("dhf003_generator_updates_baseline_register", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-003")
def test_generator_run_all_updates_change_log(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-003: DHFGenerator.run_all() populates CHANGE_LOG sentinel section when git log has commits"
    )

    dhf_root, ctx_path = _make_dhf_tree(tmp_path)

    # ChangeLogGenerator reads pyproject.toml from git_repo (tmp_path / "repo")
    git_repo = tmp_path / "repo"
    (git_repo / "pyproject.toml").write_text(
        '[project]\nname = "coronary_prj"\nversion = "0.3.0"\n'
    )

    (dhf_root / "09_cc").mkdir()
    changelog_doc = dhf_root / "09_cc" / "change_log.md"
    changelog_doc.write_text(
        "# Change Log\n\n"
        "<!-- DHF_CHANGE_LOG_START -->\n"
        "<!-- DHF_CHANGE_LOG_END -->\n"
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _mock_proc("abc1234 feat: add calcium score regressor\n")
        gen = DHFGenerator.from_config(dhf_root=dhf_root, context_file=ctx_path)
        gen.run_all()

    content = changelog_doc.read_text()
    assert "0.3.0" in content or "calcium score" in content

    report.info("run_all() populated CHANGE_LOG sentinel section from git log output", "DHF-003")
    report.auto_save("dhf003_generator_updates_change_log", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-006")
def test_generation_report_tracks_modified_files(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-006: DHFGenerationReport.files_modified lists changed files")

    dhf_root, ctx_path = _make_dhf_tree(tmp_path)
    (dhf_root / "intro.md").write_text("# {{PROJECT_NAME}}\n")

    gen = DHFGenerator.from_config(dhf_root=dhf_root, context_file=ctx_path)
    result = gen.run_all()

    modified_names = [p.name for p in result.files_modified]
    assert "intro.md" in modified_names

    report.info(f"files_modified={modified_names}", "DHF-006")
    report.auto_save("dhf006_generation_report_modified_files", evidence_output_dir)
    assert not report.has_errors, report.summary()
