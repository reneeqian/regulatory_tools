from pathlib import Path
from typing import List, Dict
import yaml

from .evidence_loader import load_latest_evidence


def _extract_requirement_ids(record) -> List[str]:
    """
    Extract requirement IDs from an evidence record.

    Supports new schema:
        "requirements": ["VER-1", "VER-2"]

    Backward compatible with:
        "requirement_ids": [...]
        "requirement_id": "VER-1"
    """
    if "requirements" in record and isinstance(record["requirements"], list):
        return record["requirements"]

    if "requirement_ids" in record:
        return record["requirement_ids"]

    if "requirement_id" in record:
        return [record["requirement_id"]]

    return []


def load_requirements(requirements_yaml: Path) -> Dict[str, dict]:
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
) -> List[dict]:

    requirements = load_requirements(requirements_yaml)

    try:
        evidence = load_latest_evidence(evidence_root)
    except RuntimeError:
        evidence = []

    # Map requirement → list of evidence records
    evidence_map: Dict[str, List[dict]] = {}

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
        matrix: List[dict],
        output: Path,
        req_coverage_summary=None,
        code_coverage_summary=None,
    ):

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

def apply_test_markers(matrix, marker_links):

    for row in matrix:

        req_id = row["requirement_id"]

        existing = set(
            t.strip() for t in row.get("tests", "").split(",") if t.strip()
        )

        markers = set(marker_links.get(req_id, []))

        row["tests"] = ", ".join(sorted(existing | markers))