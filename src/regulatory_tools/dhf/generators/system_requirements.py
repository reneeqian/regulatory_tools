from __future__ import annotations

from collections import Counter
from pathlib import Path

from regulatory_tools.dhf.generators._base import update_sentinel_section
from regulatory_tools.dhf.requirements_reader import RequirementsReader

_TAG = "SYSTEM_REQUIREMENTS"


class SystemRequirementsGenerator:
    """Generates a requirements summary table grouped by domain prefix and type."""

    def __init__(self, reader: RequirementsReader) -> None:
        self._reader = reader

    def generate_rows(self) -> str:
        reqs = self._reader.all()
        if not reqs:
            return ""

        domain_counts: Counter[str] = Counter()
        type_counts: Counter[str] = Counter()
        for r in reqs:
            domain = r.id.split("-")[0] if "-" in r.id else r.id
            domain_counts[domain] += 1
            type_counts[r.type] += 1

        lines = [
            "### By Domain",
            "",
            "| Domain | Count |",
            "|--------|-------|",
        ]
        for domain, count in sorted(domain_counts.items()):
            lines.append(f"| {domain} | {count} |")

        lines += [
            "",
            "### By Type",
            "",
            "| Type | Count |",
            "|------|-------|",
        ]
        for req_type, count in sorted(type_counts.items()):
            lines.append(f"| {req_type} | {count} |")

        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG, self.generate_rows())
