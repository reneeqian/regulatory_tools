"""
Tests for regulatory_tools.dhf.context — DHFContext (DHF-002, DHF-009).
These tests must fail before DHFContext exists.
"""

import textwrap
from pathlib import Path

import pytest

from regulatory_tools.dhf.context import DHFContext
from regulatory_tools.dhf.validator import DHFValidationError
from regulatory_tools.evidence.evidence_report import EvidenceReport


def _write_context(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "dhf_context.yaml"
    p.write_text(textwrap.dedent(content))
    return p


FULL_CONTEXT = """
    project_name: "COCA-prj"
    responsible_person: "Renee Qian"
    code_repos:
      - "Coronary_prj"
      - "medical_image_ai_toolkit"
    author: "Renee Qian"
    data_sources:
      soup: "/tmp/soup.yaml"
      evidence_runs: "/tmp/evidence_runs"
      requirements: "/tmp/requirements.yaml"
      traceability_matrix: "/tmp/traceability_matrix.md"
    templates_root: "/tmp/SaMD-DHF-Templates"
    git_repo: "/tmp/Coronary_prj"
"""


@pytest.mark.requirement("DHF-002")
def test_context_loads_required_fields(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-002: DHFContext loads all required fields from dhf_context.yaml"
    )

    path = _write_context(tmp_path, FULL_CONTEXT)
    ctx = DHFContext.from_yaml(path)

    assert ctx.project_name == "COCA-prj"
    assert ctx.responsible_person == "Renee Qian"
    assert ctx.author == "Renee Qian"
    assert "Coronary_prj" in ctx.code_repos
    assert ctx.templates_root == Path("/tmp/SaMD-DHF-Templates")
    assert ctx.git_repo == Path("/tmp/Coronary_prj")

    report.info(
        f"project_name={ctx.project_name!r}, responsible_person={ctx.responsible_person!r}",
        "DHF-002",
    )
    report.auto_save("dhf002_context_loads_required_fields", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-002")
def test_context_data_sources_are_paths(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-002: DHFContext data_sources values are Path objects")

    path = _write_context(tmp_path, FULL_CONTEXT)
    ctx = DHFContext.from_yaml(path)

    assert isinstance(ctx.data_sources["soup"], Path)
    assert isinstance(ctx.data_sources["evidence_runs"], Path)
    assert isinstance(ctx.data_sources["requirements"], Path)

    report.info("data_sources values are Path instances", "DHF-002")
    report.auto_save("dhf002_context_data_sources_paths", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-009")
def test_context_missing_required_field_raises(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-009: DHFContext.from_yaml raises DHFValidationError when a required field is missing"
    )

    missing_project_name = """
        responsible_person: "Renee Qian"
        code_repos: []
        author: "Renee Qian"
        data_sources:
          soup: "/tmp/soup.yaml"
          evidence_runs: "/tmp/evidence_runs"
          requirements: "/tmp/requirements.yaml"
          traceability_matrix: "/tmp/traceability_matrix.md"
        templates_root: "/tmp/templates"
        git_repo: "/tmp/repo"
    """
    path = _write_context(tmp_path, missing_project_name)

    with pytest.raises(DHFValidationError) as exc_info:
        DHFContext.from_yaml(path)

    assert "project_name" in str(exc_info.value)

    report.info(f"Raised DHFValidationError: {exc_info.value}", "DHF-009")
    report.auto_save("dhf009_context_missing_field_raises", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-009")
def test_context_invalid_yaml_raises(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-009: DHFContext.from_yaml raises DHFValidationError on malformed YAML"
    )

    path = tmp_path / "dhf_context.yaml"
    path.write_text("project_name: [\nbad yaml")

    with pytest.raises(DHFValidationError):
        DHFContext.from_yaml(path)

    report.info("Malformed YAML raised DHFValidationError", "DHF-009")
    report.auto_save("dhf009_context_invalid_yaml", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-002")
def test_context_as_placeholder_dict_contains_all_simple_fields(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="DHF-002: DHFContext.as_placeholder_dict() returns dict with PROJECT_NAME etc."
    )

    path = _write_context(tmp_path, FULL_CONTEXT)
    ctx = DHFContext.from_yaml(path)
    d = ctx.as_placeholder_dict()

    assert d["PROJECT_NAME"] == "COCA-prj"
    assert d["RESPONSIBLE_PERSON"] == "Renee Qian"
    assert d["AUTHOR"] == "Renee Qian"
    assert "CODE_REPO" in d

    report.info(
        "as_placeholder_dict keys include PROJECT_NAME, RESPONSIBLE_PERSON, AUTHOR, CODE_REPO",
        "DHF-002",
    )
    report.auto_save("dhf002_context_placeholder_dict", evidence_output_dir)
    assert not report.has_errors, report.summary()
