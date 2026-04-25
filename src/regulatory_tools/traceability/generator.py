from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .evidence_loader import load_latest_evidence


def _extract_requirement_ids_from_issues(record: dict[str, Any]) -> list[str]:
    issue_ids = []

    for issue in record.get("issues", []):
        requirement_id = issue.get("requirement_id")
        requirement_tag = issue.get("requirement_tag")

        if requirement_id:
            issue_ids.append(requirement_id)
        elif requirement_tag:
            issue_ids.append(requirement_tag)

    return issue_ids


def _extract_requirement_ids(record: dict[str, Any]) -> list[str]:
    """
    Extract requirement IDs from an evidence record.

    Supports new schema:
        "requirements": ["VER-1", "VER-2"]

    Backward compatible with:
        "requirement_ids": [...]
        "requirement_id": "VER-1"
    """
    if "requirements" in record and isinstance(record["requirements"], list):
        if record["requirements"]:
            return record["requirements"]

    if "requirement_ids" in record:
        if record["requirement_ids"]:
            return record["requirement_ids"]

    if "requirement_id" in record:
        return [record["requirement_id"]]

    return _extract_requirement_ids_from_issues(record)


def load_requirements(requirements_yaml: Path) -> dict[str, dict[str, str]]:
    with requirements_yaml.open() as f:
        data = yaml.safe_load(f)

    requirements = {}

    for r in data.get("requirements", []):
        requirements[r["id"]] = {
            "title": r.get("title", ""),
        }

    return requirements


def build_trace_matrix(
    requirements_yaml: Path,
    evidence_root: Path,
) -> list[dict[str, Any]]:

    requirements = load_requirements(requirements_yaml)

    try:
        evidence = load_latest_evidence(evidence_root)
    except RuntimeError:
        evidence = []

    # Map requirement → list of evidence records
    evidence_map: dict[str, list[dict[str, Any]]] = {}

    for record in evidence:
        req_ids = _extract_requirement_ids(record)

        for req in req_ids:
            evidence_map.setdefault(req, []).append(record)

    matrix = []

    for req_id, meta in requirements.items():
        records = evidence_map.get(req_id, [])

        tests = sorted({r.get("test_id", "") for r in records})
        files = sorted({r.get("_evidence_file", "") for r in records})
        results = {r.get("result", "") for r in records}

        if not records:
            status = "UNTESTED"
        elif "FAIL" in results:
            status = "FAIL"
        else:
            status = "PASS"

        matrix.append(
            {
                "requirement_id": req_id,
                "title": meta["title"],
                "tests": ", ".join(filter(None, tests)),
                "evidence_files": ", ".join(filter(None, files)),
                "status": status,
            }
        )

    return sorted(matrix, key=lambda x: x["requirement_id"])


def _sanitize_cell(text: str) -> str:
    """
    Ensure markdown table integrity:
    - Remove newlines
    - Strip whitespace
    - Escape pipe characters
    """
    if not text:
        return ""

    text = text.replace("\n", " ").strip()
    text = text.replace("|", "\\|")
    return text


def write_markdown(
        matrix: list[dict[str, Any]],
        output: Path,
        req_coverage_summary: dict[str, Any] | None = None,
        code_coverage_summary: dict[str, Any] | None = None,
        forge_health: dict[str, Any] | None = None,
    ) -> None:

    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w") as f:

        f.write("<!-- AUTO-GENERATED FILE. DO NOT EDIT MANUALLY. -->\n\n")
        f.write("# Requirements Traceability Matrix\n\n")

        # ---------------------------------------------------------
        # Requirement Coverage Summary
        # ---------------------------------------------------------

        if req_coverage_summary:

            f.write("## Requirement Coverage\n\n")

            f.write(
                f"**Coverage:** {req_coverage_summary['coverage']:.1f}% "
                f"({req_coverage_summary['tested']} / {req_coverage_summary['total']} requirements tested)\n\n"
            )

        # ---------------------------------------------------------
        # Code Coverage Summary
        # ---------------------------------------------------------

        if code_coverage_summary:

            f.write("## Code Coverage\n\n")

            coverage = code_coverage_summary.get("coverage")

            if coverage is None:
                f.write("**Line Coverage:** N/A\n\n")
            else:
                f.write(f"**Line Coverage:** {coverage:.1f}%\n\n")

            f.write(
                "Detailed uncovered lines saved in "
                "`artifacts/coverage/uncovered_lines.txt`\n\n"
            )

        # ---------------------------------------------------------
        # Forge Code Health (optional — only when forge is installed)
        # ---------------------------------------------------------

        if forge_health is not None:
            f.write("## Forge Code Health\n\n")

            score = forge_health.get("overall_score")
            grade = forge_health.get("grade", "N/A")
            generated_at = forge_health.get("generated_at", "")

            if score is not None:
                f.write(f"**Overall Score:** {score:.1%}  **Grade:** {grade}\n\n")
            else:
                f.write(f"**Overall Score:** N/A  **Grade:** {grade}\n\n")

            if generated_at:
                f.write(f"*Generated at {generated_at}*\n\n")

            collectors = forge_health.get("collectors", {})
            if collectors:
                f.write("| Collector | Score | Status |\n")
                f.write("|-----------|-------|--------|\n")
                for name, data in collectors.items():
                    display_name = name.replace("_", " ").title()
                    if data.get("skipped"):
                        reason = data.get("skip_reason") or "skipped"
                        f.write(f"| {display_name} | — | {_sanitize_cell(reason)} |\n")
                    else:
                        s = data.get("score")
                        score_cell = f"{s:.1%}" if s is not None else "—"
                        status_cell = "ok" if s is not None and s >= 0.7 else "needs attention"
                        f.write(f"| {display_name} | {score_cell} | {status_cell} |\n")
                f.write("\n")

        # ---------------------------------------------------------
        # Traceability Table
        # ---------------------------------------------------------

        f.write(
            "| Requirement ID | Title | Linked Tests | Evidence Artifacts | Status |\n"
        )
        f.write(
            "|----------------|-------------|--------------|--------------------|--------|\n"
        )

        for row in matrix:

            f.write(
                f"| {_sanitize_cell(row['requirement_id'])} "
                f"| {_sanitize_cell(row['title'])} "
                f"| {_sanitize_cell(row['tests'])} "
                f"| {_sanitize_cell(row['evidence_files'])} "
                f"| {_sanitize_cell(row['status'])} |\n"
            )


        f.write("\n\n---\n")

        if req_coverage_summary and req_coverage_summary.get("untested"):
            f.write("\n## Untested Requirements\n\n")
            for req in req_coverage_summary["untested"]:
                f.write(f"- {req}\n")

        # ---------------------------------------------------------
        # Summary Stats
        # ---------------------------------------------------------

        total = len(matrix)
        tested = sum(1 for r in matrix if r["status"] != "UNTESTED")
        failed = sum(1 for r in matrix if r["status"] == "FAIL")

        f.write("\n\n---\n")
        f.write(f"Total Requirements: {total}\n\n")
        f.write(f"Tested: {tested}\n\n")
        f.write(f"Failures: {failed}\n")

def apply_test_markers(
    matrix: list[dict[str, Any]], marker_links: dict[str, list[str]]
) -> None:

    for row in matrix:

        req_id = row["requirement_id"]

        existing = set(
            t.strip() for t in row.get("tests", "").split(",") if t.strip()
        )

        markers = set(marker_links.get(req_id, []))

        row["tests"] = ", ".join(sorted(existing | markers))

        # Marker-based linkage should count as requirement coverage even
        # when no explicit evidence record resolved back to the
        # requirement. Evidence-backed PASS/FAIL remains the stronger
        # status and is left unchanged.
        if markers and row.get("status") == "UNTESTED":
            row["status"] = "LINKED"
