"""
Tests for regulatory_tools.dhf.validator — DHFValidator (DHF-009).
These tests must fail before DHFValidator exists.
"""
import textwrap
from pathlib import Path

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport
from regulatory_tools.dhf.context import DHFContext
from regulatory_tools.dhf.validator import DHFValidator, DHFValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_SOUP = """
    - name: numpy
      version: "2.1.0"
      purpose: Numerical arrays
      license: BSD-3-Clause
"""

MINIMAL_REQUIREMENTS = """
    metadata:
      project: test
      version: 1.0
    requirements:
      - id: SYS-001
        title: Something
        description: The system shall do something.
"""

CONTEXT_TEMPLATE = """
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
"""


def _make_valid_setup(tmp_path: Path) -> tuple[DHFContext, Path]:
    """Create a minimal valid file tree and return (context, context_path)."""
    soup = tmp_path / "soup.yaml"
    soup.write_text(textwrap.dedent(MINIMAL_SOUP))

    reqs = tmp_path / "requirements.yaml"
    reqs.write_text(textwrap.dedent(MINIMAL_REQUIREMENTS))

    evidence_runs = tmp_path / "evidence_runs"
    evidence_runs.mkdir()

    traceability = tmp_path / "traceability_matrix.md"
    traceability.write_text("# Traceability Matrix\n")

    templates = tmp_path / "SaMD-DHF-Templates"
    templates.mkdir()

    git_repo = tmp_path / "repo"
    git_repo.mkdir()

    ctx_text = textwrap.dedent(CONTEXT_TEMPLATE).format(
        soup=soup,
        evidence_runs=evidence_runs,
        requirements=reqs,
        traceability_matrix=traceability,
        templates_root=templates,
        git_repo=git_repo,
    )
    ctx_path = tmp_path / "dhf_context.yaml"
    ctx_path.write_text(ctx_text)

    ctx = DHFContext.from_yaml(ctx_path)
    return ctx, ctx_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-009")
def test_validator_passes_on_valid_setup(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-009: DHFValidator.validate() passes silently when all inputs are valid")

    ctx, _ = _make_valid_setup(tmp_path)
    validator = DHFValidator(ctx)
    validator.validate()   # must not raise

    report.info("DHFValidator.validate() completed without raising", "DHF-009")
    report.auto_save("dhf009_validator_valid_setup", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-009")
def test_validator_raises_when_soup_missing(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-009: DHFValidator raises DHFValidationError when soup.yaml is missing")

    ctx, _ = _make_valid_setup(tmp_path)
    # Remove the soup file after context is loaded
    Path(ctx.data_sources["soup"]).unlink()

    with pytest.raises(DHFValidationError) as exc_info:
        DHFValidator(ctx).validate()

    assert "soup" in str(exc_info.value).lower()

    report.info(f"Missing soup.yaml raised DHFValidationError: {exc_info.value}", "DHF-009")
    report.auto_save("dhf009_validator_missing_soup", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-009")
def test_validator_raises_when_requirements_missing(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-009: DHFValidator raises when requirements.yaml is missing")

    ctx, _ = _make_valid_setup(tmp_path)
    Path(ctx.data_sources["requirements"]).unlink()

    with pytest.raises(DHFValidationError) as exc_info:
        DHFValidator(ctx).validate()

    assert "requirement" in str(exc_info.value).lower()

    report.info(f"Missing requirements.yaml raised DHFValidationError", "DHF-009")
    report.auto_save("dhf009_validator_missing_requirements", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-009")
def test_validator_raises_when_evidence_runs_dir_missing(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-009: DHFValidator raises when evidence_runs directory does not exist")

    ctx, _ = _make_valid_setup(tmp_path)
    import shutil
    shutil.rmtree(ctx.data_sources["evidence_runs"])

    with pytest.raises(DHFValidationError) as exc_info:
        DHFValidator(ctx).validate()

    assert "evidence" in str(exc_info.value).lower()

    report.info(f"Missing evidence_runs dir raised DHFValidationError", "DHF-009")
    report.auto_save("dhf009_validator_missing_evidence_runs", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-009")
def test_validator_collects_all_violations_before_raising(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-009: DHFValidator reports all violations, not just the first")

    ctx, _ = _make_valid_setup(tmp_path)
    # Remove two files at once
    Path(ctx.data_sources["soup"]).unlink()
    Path(ctx.data_sources["requirements"]).unlink()

    with pytest.raises(DHFValidationError) as exc_info:
        DHFValidator(ctx).validate()

    error_text = str(exc_info.value)
    assert "soup" in error_text.lower()
    assert "requirement" in error_text.lower()

    report.info(f"Two missing files → single DHFValidationError with both mentioned", "DHF-009")
    report.auto_save("dhf009_validator_all_violations", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-009")
def test_validator_raises_when_requirements_yaml_has_duplicate_ids(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-009: DHFValidator raises when requirements.yaml has duplicate IDs")

    ctx, _ = _make_valid_setup(tmp_path)
    Path(ctx.data_sources["requirements"]).write_text(textwrap.dedent("""
        metadata:
          project: test
          version: 1.0
        requirements:
          - id: SYS-001
            title: First
            description: First.
          - id: SYS-001
            title: Duplicate
            description: Duplicate.
    """))

    with pytest.raises(DHFValidationError) as exc_info:
        DHFValidator(ctx).validate()

    assert "SYS-001" in str(exc_info.value)

    report.info(f"Duplicate SYS-001 raised DHFValidationError", "DHF-009")
    report.auto_save("dhf009_validator_duplicate_ids", evidence_output_dir)
    assert not report.has_errors, report.summary()
