"""
Tests for the regulatory_tools.dhf CLI entry point (DHF-017).
These tests fail until regulatory_tools/dhf/__main__.py is implemented.
"""

import json
import sys
import textwrap
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport


def _write_relative_context(dest: Path) -> Path:
    p = dest / "dhf_context.yaml"
    p.write_text(textwrap.dedent("""\
        project_name: "Test Project"
        responsible_person: "Test User"
        code_repos: ["test_repo"]
        author: "Test User"
        data_sources:
          soup: "docs/soup.yaml"
          evidence_runs: "artifacts/evidence_runs"
          requirements: "docs/requirements.yaml"
          traceability_matrix: "docs/traceability_matrix.md"
        templates_root: "templates"
        git_repo: "."
    """))
    return p


@pytest.mark.requirement("DHF-017")
def test_cli_missing_context_exits_nonzero(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-017: CLI exits non-zero and reports missing dhf_context.yaml"
    )

    from regulatory_tools.dhf.__main__ import main  # fails until implemented

    dhf_root = tmp_path / "dhf_root"
    dhf_root.mkdir()
    # No dhf_context.yaml written — should trigger exit 1

    stderr_buf = StringIO()
    with patch("sys.argv", ["regulatory-generate-dhf", str(dhf_root)]):
        with patch("sys.stderr", stderr_buf):
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code != 0
    assert "dhf_context.yaml" in stderr_buf.getvalue().lower()

    report.info(f"Exit code: {exc_info.value.code}", "DHF-017")
    report.auto_save("dhf017_cli_missing_context_exits_nonzero", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-017")
def test_cli_produces_json_with_required_keys(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-017: CLI prints valid JSON with files_modified and unfilled_vars on success"
    )

    from regulatory_tools.dhf.__main__ import main  # fails until implemented
    from regulatory_tools.dhf.generator import DHFGenerationReport

    dhf_root = tmp_path / "dhf_root"
    dhf_root.mkdir()
    base_dir = tmp_path / "primary_repo"
    base_dir.mkdir()
    _write_relative_context(dhf_root)

    mock_report = DHFGenerationReport(
        files_modified=[Path("02_requirements/system_requirements.md")],
        unfilled_vars=[(Path("some.md"), "PLACEHOLDER_X")],
        scaffolded_sections=[],
    )

    stdout_buf = StringIO()
    with patch("regulatory_tools.dhf.generator.DHFGenerator.run_all", return_value=mock_report):
        with patch("regulatory_tools.dhf.validator.DHFValidator.validate"):
            with patch("sys.argv", [
                "regulatory-generate-dhf", str(dhf_root), "--base-dir", str(base_dir),
            ]):
                with patch("sys.stdout", stdout_buf):
                    main()

    output = json.loads(stdout_buf.getvalue())
    assert "files_modified" in output
    assert "unfilled_vars" in output
    assert len(output["files_modified"]) == 1
    assert len(output["unfilled_vars"]) == 1

    report.info(f"JSON keys present: {list(output.keys())}", "DHF-017")
    report.auto_save("dhf017_cli_json_required_keys", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-017")
def test_cli_passes_base_dir_to_context(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-017: --base-dir arg is forwarded to DHFContext.from_yaml as base_dir"
    )

    from regulatory_tools.dhf.__main__ import main  # fails until implemented
    from regulatory_tools.dhf.context import DHFContext
    from regulatory_tools.dhf.generator import DHFGenerationReport

    dhf_root = tmp_path / "dhf_root"
    dhf_root.mkdir()
    base_dir = tmp_path / "primary_repo"
    base_dir.mkdir()
    _write_relative_context(dhf_root)

    captured: list[Path | None] = []
    original = DHFContext.from_yaml.__func__ if hasattr(DHFContext.from_yaml, "__func__") else DHFContext.from_yaml

    def spy_from_yaml(path: Path, base_dir: Path | None = None) -> DHFContext:
        captured.append(base_dir)
        return original(path, base_dir=base_dir)

    with patch.object(DHFContext, "from_yaml", staticmethod(spy_from_yaml)):
        with patch("regulatory_tools.dhf.generator.DHFGenerator.run_all", return_value=DHFGenerationReport()):
            with patch("regulatory_tools.dhf.validator.DHFValidator.validate"):
                with patch("sys.argv", [
                    "regulatory-generate-dhf", str(dhf_root), "--base-dir", str(base_dir),
                ]):
                    with patch("sys.stdout", StringIO()):
                        main()

    assert captured, "from_yaml was never called"
    assert captured[0] == base_dir.resolve()

    report.info(f"base_dir passed to from_yaml: {captured[0]}", "DHF-017")
    report.auto_save("dhf017_cli_base_dir_forwarded", evidence_output_dir)
    assert not report.has_errors, report.summary()
