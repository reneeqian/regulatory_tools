from pathlib import Path
from regulatory_tools.traceability.pipeline import generate_traceability_matrix


def test_pipeline_execution(tmp_path):

    project = tmp_path / "proj"

    (project / "docs").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "artifacts" / "evidence_runs").mkdir(parents=True)

    (project / "docs" / "requirements.yaml").write_text(
        """
requirements:
  - id: CAC-REQ-001
    description: example
"""
    )

    generate_traceability_matrix(project)

    output = project / "docs" / "traceability_matrix.md"

    assert output.exists()