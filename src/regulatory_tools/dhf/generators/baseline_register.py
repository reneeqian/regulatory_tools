from __future__ import annotations

import subprocess
from pathlib import Path

from regulatory_tools.dhf.generators._base import update_sentinel_section

_TAG = "BASELINE_REGISTER"


class BaselineRegisterGenerator:
    """Generates the baseline register table from git tags."""

    def __init__(self, git_repo: Path) -> None:
        self._repo = git_repo

    def generate_rows(self) -> str:
        tags_out = subprocess.run(
            ["git", "tag", "-l", "--sort=version:refname"],
            capture_output=True, text=True, cwd=self._repo,
        ).stdout.strip()

        if not tags_out:
            return ""

        tags = [t for t in tags_out.splitlines() if t]
        lines = ["| Version | SHA | Date |", "|---------|-----|------|"]
        for tag in tags:
            sha = subprocess.run(
                ["git", "rev-parse", tag],
                capture_output=True, text=True, cwd=self._repo,
            ).stdout.strip()[:12]
            date = subprocess.run(
                ["git", "log", "-1", "--format=%ci", tag],
                capture_output=True, text=True, cwd=self._repo,
            ).stdout.strip()
            lines.append(f"| {tag} | {sha} | {date} |")

        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG, self.generate_rows())
