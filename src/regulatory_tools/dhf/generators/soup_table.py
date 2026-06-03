from __future__ import annotations

from pathlib import Path

import yaml

from regulatory_tools.dhf.generators._base import update_sentinel_section

_TAG = "SOUP_TABLE"


class SOUPTableGenerator:
    """Generates the SOUP register markdown table from soup.yaml."""

    def __init__(self, soup_yaml: Path) -> None:
        self._path = soup_yaml

    def generate_rows(self) -> str:
        with open(self._path) as f:
            data = yaml.safe_load(f)
        entries = data.get("soup", [])
        if not entries:
            return ""
        lines = ["| Name | Version | Purpose | License |",
                 "|------|---------|---------|---------|"]
        for e in entries:
            lines.append(
                f"| {e.get('name', '')} | {e.get('version', '')} "
                f"| {e.get('purpose', '')} | {e.get('license', '')} |"
            )
        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG, self.generate_rows())
