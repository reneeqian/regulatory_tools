from __future__ import annotations

from pathlib import Path

import yaml

from regulatory_tools.dhf.generators._base import update_sentinel_section

_TAG = "HAZARD_ANALYSIS"
_FILL = "<!-- FILL -->"


class HazardAnalysisGenerator:
    """Generates scaffold rows for hazard_analysis.md from hazard_analysis.yaml.

    Narrative fields (cause, effect, severity, probability) are rendered from
    the YAML when present; entries without them get <!-- FILL --> placeholders
    so manual completion is clearly flagged.
    """

    def __init__(self, hazard_yaml: Path) -> None:
        self._path = hazard_yaml

    def generate_rows(self) -> str:
        with self._path.open() as f:
            data = yaml.safe_load(f)

        hazards = data.get("hazards", [])
        if not hazards:
            return ""

        lines = [
            "| ID | Hazard | Cause | Effect | Severity | Probability | Mitigation |",
            "|----|--------|-------|--------|----------|-------------|------------|",
        ]
        for h in hazards:
            haz_id = h.get("id", "")
            hazard = h.get("hazard", "")
            cause = h.get("cause") or _FILL
            effect = h.get("effect") or _FILL
            severity = h.get("severity") or _FILL
            probability = h.get("probability") or _FILL
            mitigation = h.get("mitigation_ref") or _FILL
            lines.append(
                f"| {haz_id} | {hazard} | {cause} | {effect} | {severity} | {probability} | {mitigation} |"
            )
        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG, self.generate_rows())
