from pathlib import Path

from .generator import build_trace_matrix, write_markdown, apply_test_markers
from .validate_traceability import validate_traceability, find_unmarked_tests
from .coverage import compute_requirement_coverage
from .coverage import compute_code_coverage, save_uncovered_lines
from .test_scanner import collect_requirement_markers


def generate_traceability_matrix(project_root: Path):

    TEST_DIR = project_root / "tests"
    REQUIREMENTS_YAML = project_root / "docs" / "requirements.yaml"
    EVIDENCE_ROOT = project_root / "artifacts" / "evidence_runs"
    OUTPUT_MATRIX = project_root / "docs" / "traceability_matrix.md"

    missing, untracked = validate_traceability(
        requirements_yaml=REQUIREMENTS_YAML,
        test_dir=TEST_DIR,
    )

    unmarked_tests = find_unmarked_tests(TEST_DIR)
    marker_links = collect_requirement_markers(TEST_DIR, project_root)

    matrix = build_trace_matrix(
        requirements_yaml=REQUIREMENTS_YAML,
        evidence_root=EVIDENCE_ROOT,
    )

    apply_test_markers(matrix, marker_links)

    coverage, tested_count, total_count, untested = compute_requirement_coverage(matrix)

    code_coverage, uncovered = compute_code_coverage(project_root)

    save_uncovered_lines(project_root, uncovered)

    write_markdown(
        matrix,
        OUTPUT_MATRIX,
        req_coverage_summary={
            "coverage": coverage,
            "tested": tested_count,
            "total": total_count,
            "untested": untested,
        },
        code_coverage_summary={
            "coverage": code_coverage
        }
    )