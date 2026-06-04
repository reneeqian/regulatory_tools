from __future__ import annotations

import sys
from pathlib import Path

from ..traceability.pipeline import generate_traceability_matrix
from .pytest_runner import run_pytest_with_coverage

_GRADE_ORDER: dict[str, int] = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


def run_tests_and_trace(project_root: Path, min_grade: str | None = "B", *, update_readme: bool = True) -> None:
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
    _run_quality_checks(project_root)
    forge_summary = generate_traceability_matrix(project_root)
    _check_linked_gate(project_root)

    if forge_summary is None:
        print("[run_tests_and_trace] forge not installed — skipping grade check and README update.")
        return

    from ..quality.forge_integration import update_readme_forge_health, write_forge_health_to_summary
    if update_readme:
        update_readme_forge_health(project_root, forge_summary)
    else:
        write_forge_health_to_summary(forge_summary)

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


def _check_linked_gate(project_root: Path) -> None:
    from ..quality.linked_checker import check_linked_requirements
    result = check_linked_requirements(project_root)
    if result["skipped"]:
        return
    if result["linked_ids"]:
        ids = ", ".join(result["linked_ids"])
        print(f"[FAIL] {len(result['linked_ids'])} LINKED requirement(s) — tests exist but no evidence: {ids}")
        print("[FAIL] Add EvidenceReport.auto_save() to each linked test to convert LINKED → PASS.")
        sys.exit(1)
    print(f"[OK] LINKED gate: 0 LINKED requirements")


def _run_quality_checks(project_root: Path) -> None:
    from ..quality.soup_checker import check_soup_inventory, check_soup_fields
    from ..quality.rsk_checker import check_rsk_requirements
    from ..quality.anomaly_checker import check_anomaly_log
    from ..quality.version_checker import check_version_baseline

    soup = check_soup_inventory(project_root)
    if not soup["found"]:
        print("[WARN] docs/soup.yaml not found — SOUP inventory missing")
    elif soup["unlisted_deps"]:
        print(f"[WARN] SOUP inventory missing entries: {soup['unlisted_deps']}")
    else:
        print(f"[OK] SOUP inventory found: {soup['soup_path']}")

    fields = check_soup_fields(project_root)
    if fields["found"] and fields["violations"]:
        for v in fields["violations"]:
            print(f"[WARN] SOUP field: {v}")
    elif fields["found"]:
        print("[OK] SOUP field completeness: all entries valid")

    rsk = check_rsk_requirements(project_root)
    if not rsk["found"]:
        print("[WARN] No RSK- requirements found in docs/requirements.yaml — risk management gap")
    else:
        print(f"[OK] RSK requirements present: {rsk['rsk_ids']}")

    anomaly = check_anomaly_log(project_root)
    if anomaly["skipped"]:
        print("[OK] Anomaly log check skipped (samd_class: utility)")
    elif not anomaly["found"]:
        for v in anomaly["violations"]:
            print(f"[WARN] Anomaly log: {v}")
    else:
        print("[OK] docs/anomaly_log.yaml present")

    version = check_version_baseline(project_root)
    if not version["found"]:
        print("[WARN] pyproject.toml not found — version baseline check skipped")
    elif not version["has_tags"]:
        print(f"[WARN] Version: {version['warning']}")
    elif version["violations"]:
        for v in version["violations"]:
            print(f"[WARN] Version: {v}")
    else:
        print(f"[OK] Version baseline: {version['pyproject_version']} matches tag v{version['latest_tag']}")
