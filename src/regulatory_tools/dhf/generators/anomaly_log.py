from __future__ import annotations

from pathlib import Path

import yaml

from regulatory_tools.dhf.generators._base import update_sentinel_section

_TAG_TABLE = "ANOMALY_TABLE"
_TAG_UNRESOLVED = "UNRESOLVED_ANOMALIES"
_OPEN_STATUSES = {"open", "in_progress", "deferred"}

_TABLE_HEADER = (
    "| ID | Discovered | Severity | Status | Description"
    " | Safety Impact | Resolution | Linked PR | Closed |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)
_UNRESOLVED_HEADER = (
    "| ANO-ID | Severity | Rationale for Deferral |\n"
    "|---|---|---|\n"
)


class AnomalyLogGenerator:
    """Generates anomaly log table sections from anomaly_log.yaml."""

    def __init__(self, anomaly_yaml: Path) -> None:
        self._path = anomaly_yaml

    def _load(self) -> list[dict]:
        with open(self._path) as f:
            data = yaml.safe_load(f)
        return data.get("anomalies") or []

    def generate_table_rows(self) -> str:
        entries = self._load()
        if not entries:
            return _TABLE_HEADER
        lines = [_TABLE_HEADER.rstrip("\n")]
        for e in entries:
            lines.append(
                f"| {e.get('id', '—')} "
                f"| {e.get('date', '—')} "
                f"| {e.get('severity', '—')} "
                f"| {e.get('status', '—')} "
                f"| {e.get('summary', '—')} "
                f"| {e.get('safety_impact', '—')} "
                f"| {e.get('resolution', '—')} "
                f"| {e.get('linked_pr', '—')} "
                f"| {e.get('closed', '—')} |"
            )
        return "\n".join(lines) + "\n"

    def generate_unresolved_rows(self) -> str:
        entries = self._load()
        open_entries = [
            e for e in entries
            if str(e.get("status", "")).lower() in _OPEN_STATUSES
        ]
        if not open_entries:
            return _UNRESOLVED_HEADER + "| — | — | — |\n"
        lines = [_UNRESOLVED_HEADER.rstrip("\n")]
        for e in open_entries:
            lines.append(
                f"| {e.get('id', '—')} "
                f"| {e.get('severity', '—')} "
                f"| {e.get('resolution', '—')} |"
            )
        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG_TABLE, self.generate_table_rows())
        update_sentinel_section(path, _TAG_UNRESOLVED, self.generate_unresolved_rows())
