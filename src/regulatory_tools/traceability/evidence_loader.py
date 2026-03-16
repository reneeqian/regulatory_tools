import json
from pathlib import Path
from typing import List, Dict, Any

def load_latest_evidence(root: Path):

    if not root.exists():
        return []

    evidence_runs = sorted(p for p in root.iterdir() if p.is_dir())

    if not evidence_runs:
        return []

    latest = evidence_runs[-1]

    records = []

    for file in latest.glob("*.json"):
        try:
            records.append(json.loads(file.read_text()))
        except Exception:
            continue

    return records