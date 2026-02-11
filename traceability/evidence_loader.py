import json
from pathlib import Path
from typing import List, Dict, Any

def load_latest_evidence(root: Path) -> List[Dict[str, Any]]:
    runs = sorted(p for p in root.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No evidence runs found")

    latest_run = runs[-1]

    records: List[Dict[str, Any]] = []
    for path in latest_run.glob("*.json"):
        with open(path) as f:
            record = json.load(f)
            record["_evidence_file"] = path.name
            records.append(record)

    return records