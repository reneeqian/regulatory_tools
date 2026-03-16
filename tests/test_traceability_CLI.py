from regulatory_tools.traceability.pipeline import generate_traceability_matrix
from pathlib import Path


def test_traceability_cli_execution(tmp_path):

    project = tmp_path / "proj"

    (project / "docs").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "artifacts" / "evidence_runs").mkdir(parents=True)

    (project / "docs" / "requirements.yaml").write_text(
        """
requirements:
  - id: VER-001
    description: example
"""
    )

    generate_traceability_matrix(project)

    assert (project / "docs" / "traceability_matrix.md").exists()