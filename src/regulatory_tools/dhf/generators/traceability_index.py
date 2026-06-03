from __future__ import annotations

import re
from pathlib import Path

from regulatory_tools.dhf.generators._base import update_sentinel_section

_TAG = "TRACEABILITY_INDEX"
_COVERAGE_RE = re.compile(r"\*\*Coverage:\*\*\s*([0-9.]+%[^)]*\))")
_SCORE_RE = re.compile(r"\*\*Overall Score:\*\*\s*([0-9.]+%)")
_GRADE_RE = re.compile(r"\*\*Grade:\*\*\s*(\w+)")


class TraceabilityIndexGenerator:
    """Parses coverage and forge grade stats from a generated traceability matrix."""

    def __init__(self, traceability_matrix_path: Path) -> None:
        self._path = traceability_matrix_path

    def generate_rows(self) -> str:
        content = self._path.read_text()
        coverage = _COVERAGE_RE.search(content)
        score = _SCORE_RE.search(content)
        grade = _GRADE_RE.search(content)

        lines = ["| Metric | Value |", "|--------|-------|"]
        if coverage:
            lines.append(f"| Requirement Coverage | {coverage.group(1)} |")
        if score:
            lines.append(f"| Overall Score | {score.group(1)} |")
        if grade:
            lines.append(f"| Grade | {grade.group(1)} |")

        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG, self.generate_rows())
