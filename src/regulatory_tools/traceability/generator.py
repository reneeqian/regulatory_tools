from pathlib import Path
from typing import List, Dict
import yaml

from .evidence_loader import load_latest_evidence


def _extract_requirement_ids(record) -> List[str]:
    """
    Extract requirement IDs from an evidence record.

    Supports new schema:
        "requirements": ["REQ-1", "REQ-2"]

    Backward compatible with:
        "requirement_ids": [...]
        "requirement_id": "REQ-1"
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
            "description": r.get("description", ""),
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
                "description": meta["description"],
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


def write_markdown(matrix: List[dict], output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w") as f:
        f.write("# Requirements Traceability Matrix\n\n")

        f.write(
            "| Requirement ID | Description | Linked Tests | Evidence Artifacts | Status |\n"
        )
        f.write(
            "|----------------|-------------|--------------|--------------------|--------|\n"
        )

        for row in matrix:
            f.write(
                f"| {_sanitize_cell(row['requirement_id'])} "
                f"| {_sanitize_cell(row['description'])} "
                f"| {_sanitize_cell(row['tests'])} "
                f"| {_sanitize_cell(row['evidence_files'])} "
                f"| {_sanitize_cell(row['status'])} |\n"
            )

