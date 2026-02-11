import json
from pathlib import Path
from typing import List, Dict, Any

def load_latest_evidence(root: Path) -> List[Dict[str, Any]]:
    evidence_runs = sorted(p for p in root.iterdir() if p.is_dir())
    if not evidence_runs:
        raise RuntimeError(
            "No evidence runs found.\n\n"
            "Expected at least one evidence directory under:\n"
            f"  {root.resolve()}\n\n"
            "Run pytest with evidence generation enabled before "
            "generating traceability."
        )

    latest_run = evidence_runs[-1]

    records: List[Dict[str, Any]] = []
    for path in latest_run.glob("*.json"):
        with open(path) as f:
            record = json.load(f)
            record["_evidence_file"] = path.name
            records.append(record)

    return records