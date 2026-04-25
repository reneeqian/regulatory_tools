from __future__ import annotations

import sys
from pathlib import Path

from ..traceability.pipeline import generate_traceability_matrix
from .pytest_runner import run_pytest_with_coverage

_GRADE_ORDER: dict[str, int] = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


def run_tests_and_trace(project_root: Path, min_grade: str | None = "B") -> None:
    """
    Full verification pipeline for regulated projects.

    Runs:
        1. pytest
        2. code coverage
        3. requirement traceability validation
        4. traceability matrix generation
        5. uncovered code reporting
        6. forge health grade check (exits 1 if grade < min_grade)
        7. README forge health section update
    """
    run_pytest_with_coverage(project_root)
    forge_summary = generate_traceability_matrix(project_root)

    if forge_summary is None:
        print("[run_tests_and_trace] forge not installed — skipping grade check and README update.")
        return

    from ..quality.forge_integration import update_readme_forge_health
    update_readme_forge_health(project_root, forge_summary)

    grade = forge_summary.get("grade", "N/A")
    score = forge_summary.get("overall_score")
    score_display = f"{score:.2f}" if score is not None else "N/A"

    if min_grade is None:
        print(f"[forge] Grade: {grade} (score: {score_display}) — grade enforcement disabled.")
        return

    min_rank = _GRADE_ORDER.get(min_grade, 3)
    actual_rank = _GRADE_ORDER.get(grade, -1)

    print(f"[forge] Grade: {grade} (score: {score_display}) — minimum required: {min_grade}")

    if actual_rank < min_rank:
        print(f"[forge] Grade {grade} is below the required minimum {min_grade}. Failing CI.")
        sys.exit(1)
