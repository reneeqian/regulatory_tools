from pathlib import Path

from ..traceability.pipeline import generate_traceability_matrix
from .pytest_runner import run_pytest_with_coverage


def run_tests_and_trace(project_root: Path):
    """
    Full verification pipeline for regulated projects.

    Runs:
        1. pytest
        2. code coverage
        3. requirement traceability validation
        4. traceability matrix generation
        5. uncovered code reporting
    """

    run_pytest_with_coverage(project_root)
    generate_traceability_matrix(project_root)
