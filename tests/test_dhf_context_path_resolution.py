"""
Tests for DHFContext.from_yaml() base_dir path resolution (DHF-017).
These tests fail until DHFContext.from_yaml() gains the base_dir parameter.
"""

import textwrap
from pathlib import Path

import pytest

from regulatory_tools.dhf.context import DHFContext
from regulatory_tools.evidence.evidence_report import EvidenceReport


def _write_relative_context(dest: Path) -> Path:
    """Write a dhf_context.yaml that uses relative paths throughout."""
    p = dest / "dhf_context.yaml"
    p.write_text(textwrap.dedent("""\
        project_name: "Test Project"
        responsible_person: "Test User"
        code_repos:
          - "test_repo"
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
def test_relative_paths_resolve_against_base_dir(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-017: relative paths in dhf_context.yaml resolve against base_dir"
    )

    base_dir = tmp_path / "primary_repo"
    base_dir.mkdir()
    ctx_path = _write_relative_context(tmp_path)

    ctx = DHFContext.from_yaml(ctx_path, base_dir=base_dir)

    assert ctx.data_sources["soup"] == (base_dir / "docs/soup.yaml").resolve()
    assert ctx.data_sources["evidence_runs"] == (base_dir / "artifacts/evidence_runs").resolve()
    assert ctx.data_sources["traceability_matrix"] == (base_dir / "docs/traceability_matrix.md").resolve()
    assert ctx.templates_root == (base_dir / "templates").resolve()
    assert ctx.git_repo == base_dir.resolve()

    report.info(
        f"soup={ctx.data_sources['soup']}, base_dir={base_dir}",
        "DHF-017",
    )
    report.auto_save("dhf017_relative_paths_resolve_against_base_dir", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-017")
def test_absolute_paths_unchanged_when_base_dir_provided(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-017: absolute paths in dhf_context.yaml are unchanged even when base_dir is given"
    )

    base_dir = tmp_path / "primary_repo"
    base_dir.mkdir()

    ctx_path = tmp_path / "dhf_context.yaml"
    ctx_path.write_text(textwrap.dedent("""\
        project_name: "Test Project"
        responsible_person: "Test User"
        code_repos: ["test_repo"]
        author: "Test User"
        data_sources:
          soup: "/absolute/path/soup.yaml"
          evidence_runs: "/absolute/path/evidence_runs"
          requirements: "/absolute/path/requirements.yaml"
          traceability_matrix: "/absolute/path/traceability_matrix.md"
        templates_root: "/absolute/templates"
        git_repo: "/absolute/repo"
    """))

    ctx = DHFContext.from_yaml(ctx_path, base_dir=base_dir)

    assert ctx.data_sources["soup"] == Path("/absolute/path/soup.yaml")
    assert ctx.templates_root == Path("/absolute/templates")
    assert ctx.git_repo == Path("/absolute/repo")

    report.info("Absolute paths preserved unchanged when base_dir provided", "DHF-017")
    report.auto_save("dhf017_absolute_paths_unchanged_with_base_dir", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-017")
def test_relative_requirements_list_resolved(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-017: a list of relative requirements paths all resolve against base_dir"
    )

    base_dir = tmp_path / "primary_repo"
    base_dir.mkdir()

    ctx_path = tmp_path / "dhf_context.yaml"
    ctx_path.write_text(textwrap.dedent("""\
        project_name: "Test Project"
        responsible_person: "Test User"
        code_repos: ["test_repo"]
        author: "Test User"
        data_sources:
          soup: "docs/soup.yaml"
          evidence_runs: "artifacts/evidence_runs"
          requirements:
            - "docs/requirements.yaml"
            - "docs/design.yaml"
          traceability_matrix: "docs/traceability_matrix.md"
        templates_root: "templates"
        git_repo: "."
    """))

    ctx = DHFContext.from_yaml(ctx_path, base_dir=base_dir)

    assert ctx.requirement_paths == [
        (base_dir / "docs/requirements.yaml").resolve(),
        (base_dir / "docs/design.yaml").resolve(),
    ]

    report.info(f"requirement_paths={ctx.requirement_paths}", "DHF-017")
    report.auto_save("dhf017_relative_requirements_list_resolved", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-017")
def test_no_base_dir_preserves_existing_behaviour(tmp_path, evidence_output_dir):
    """Without base_dir the existing contract is unchanged — no regression (DHF-002)."""
    report = EvidenceReport(
        subject="DHF-017: from_yaml without base_dir keeps existing path behaviour (backwards compat)"
    )

    ctx_path = tmp_path / "dhf_context.yaml"
    ctx_path.write_text(textwrap.dedent("""\
        project_name: "Test Project"
        responsible_person: "Test User"
        code_repos: ["test_repo"]
        author: "Test User"
        data_sources:
          soup: "/tmp/soup.yaml"
          evidence_runs: "/tmp/evidence_runs"
          requirements: "/tmp/requirements.yaml"
          traceability_matrix: "/tmp/traceability_matrix.md"
        templates_root: "/tmp/templates"
        git_repo: "/tmp/repo"
    """))

    ctx = DHFContext.from_yaml(ctx_path)

    assert ctx.data_sources["soup"] == Path("/tmp/soup.yaml")
    assert ctx.git_repo == Path("/tmp/repo")

    report.info("No base_dir: absolute paths unchanged — backwards compatible", "DHF-017")
    report.auto_save("dhf017_no_base_dir_backwards_compat", evidence_output_dir)
    assert not report.has_errors, report.summary()
