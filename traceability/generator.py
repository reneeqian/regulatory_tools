from pathlib import Path
from typing import List

from .models import TraceRow
from .evidence_loader import load_latest_evidence

def _extract_requirement_ids(record) -> List[str]:
    if "requirement_ids" in record:
        return record["requirement_ids"]
    if "requirement_id" in record:
        return [record["requirement_id"]]
    return []

def generate_trace_rows(evidence_root: Path) -> List[TraceRow]:
    evidence = load_latest_evidence(evidence_root)
    rows: List[TraceRow] = []

    for record in evidence:
        test_id = record.get("test_id")
        result = record.get("result")
        evidence_file = record.get("_evidence_file")

        for req_id in _extract_requirement_ids(record):
            rows.append(
                TraceRow(
                    requirement_id=req_id,
                    test_id=test_id,
                    evidence_file=evidence_file,
                    result=result,
                )
            )

    return rows

def write_markdown(rows: List[TraceRow], output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w") as f:
        f.write("# Traceability Matrix\n\n")
        f.write("| Requirement ID | Test ID | Evidence Artifact | Result |\n")
        f.write("|---------------|--------|------------------|--------|\n")

        for r in sorted(rows, key=lambda x: (x.requirement_id, x.test_id)):
            f.write(
                f"| {r.requirement_id} | "
                f"{r.test_id} | "
                f"{r.evidence_file} | "
                f"{r.result} |\n"
            )
