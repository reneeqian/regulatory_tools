from __future__ import annotations

import json
from pathlib import Path

from regulatory_tools.dhf.generators._base import update_sentinel_section

_TAG = "EVIDENCE_INDEX"


class EvidenceIndexGenerator:
    """Generates the evidence index table from EvidenceReport JSON artifacts."""

    def __init__(self, evidence_runs_dir: Path) -> None:
        self._dir = evidence_runs_dir

    def _latest_run_dir(self) -> Path | None:
        run_dirs = sorted(p for p in self._dir.iterdir() if p.is_dir())
        return run_dirs[-1] if run_dirs else None

    def generate_rows(self) -> str:
        latest = self._latest_run_dir()
        if latest is None:
            return ""
        json_files = sorted(latest.glob("*.json"))
        if not json_files:
            return ""
        lines = [
            f"*Latest run: `{latest.name}`*",
            "",
            "| Test ID | Subject | Result | Requirements | Timestamp |",
            "|---------|---------|--------|--------------|-----------|",
        ]
        for jf in json_files:
            try:
                data = json.loads(jf.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            test_id = data.get("test_id") or jf.stem
            subject = data.get("subject", "")
            result = data.get("result", "")
            tags = ", ".join(data.get("requirement_tags", []))
            timestamp = data.get("timestamp", "")
            lines.append(f"| {test_id} | {subject} | {result} | {tags} | {timestamp} |")
        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG, self.generate_rows())
