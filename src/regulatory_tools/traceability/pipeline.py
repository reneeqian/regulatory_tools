from pathlib import Path

from .generator import build_trace_matrix, write_markdown, apply_test_markers
from .validate_traceability import validate_traceability, find_unmarked_tests
from .coverage import compute_requirement_coverage
from .coverage import compute_code_coverage, save_uncovered_lines
from .test_scanner import collect_requirement_markers


def generate_traceability_matrix(project_root):
    
    (project_root / "artifacts").mkdir(exist_ok=True)
    (project_root / "artifacts" / "evidence_runs").mkdir(exist_ok=True)
    (project_root / "artifacts" / "coverage").mkdir(exist_ok=True)

    test_dir = project_root / "tests"
    requirements_yaml = project_root / "docs" / "requirements.yaml"
    evidence_root = project_root / "artifacts" / "evidence_runs"
    output = project_root / "docs" / "traceability_matrix.md"

    marker_links = collect_requirement_markers(test_dir, project_root)

    matrix = build_trace_matrix(
        requirements_yaml=requirements_yaml,
        evidence_root=evidence_root,
    )

    apply_test_markers(matrix, marker_links)

    coverage, tested, total, untested = compute_requirement_coverage(matrix)

    code_coverage, uncovered = compute_code_coverage(project_root)

    save_uncovered_lines(project_root, uncovered)

    write_markdown(
        matrix,
        output,
        req_coverage_summary={
            "coverage": coverage,
            "tested": tested,
            "total": total,
            "untested": untested,
        },
        code_coverage_summary={
            "coverage": code_coverage
        },
    )