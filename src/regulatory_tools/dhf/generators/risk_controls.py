from __future__ import annotations

from pathlib import Path

from regulatory_tools.dhf.generators._base import update_sentinel_section
from regulatory_tools.dhf.requirements_reader import RequirementsReader

_TAG = "RISK_CONTROLS"


class RiskControlsGenerator:
    """Generates partial risk_control_measures rows from RSK requirements."""

    def __init__(self, reader: RequirementsReader) -> None:
        self._reader = reader

    def generate_rows(self) -> str:
        rsk_reqs = self._reader.by_type("risk_control")
        if not rsk_reqs:
            return ""
        lines = [
            "| ID | Title | Control Measure | Implementation | Derived From |",
            "|----|-------|-----------------|----------------|--------------|",
        ]
        for r in rsk_reqs:
            derived = ", ".join(r.derived_from) if r.derived_from else "—"
            lines.append(
                f"| {r.id} | {r.title} | <!-- FILL --> | <!-- FILL --> | {derived} |"
            )
        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG, self.generate_rows())
