from __future__ import annotations

import re
import subprocess
from pathlib import Path

from regulatory_tools.dhf.generators._base import update_sentinel_section

_TAG = "CHANGE_LOG"
_VERSION_RE = re.compile(r'^\s*version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _read_version(pyproject_toml: Path) -> str:
    match = _VERSION_RE.search(pyproject_toml.read_text())
    return match.group(1) if match else "unknown"


class ChangeLogGenerator:
    """Generates the change log table from git log and pyproject.toml version."""

    def __init__(self, git_repo: Path, pyproject_toml: Path) -> None:
        self._repo = git_repo
        self._pyproject = pyproject_toml

    def generate_rows(self) -> str:
        version = _read_version(self._pyproject)
        log_out = subprocess.run(
            ["git", "log", "--oneline", "--no-merges"],
            capture_output=True, text=True, cwd=self._repo,
        ).stdout.strip()

        if not log_out:
            return ""

        lines = [
            "| Version | SHA | Description |",
            "|---------|-----|-------------|",
        ]
        for line in log_out.splitlines():
            parts = line.split(" ", 1)
            sha = parts[0] if parts else ""
            msg = parts[1] if len(parts) > 1 else ""
            lines.append(f"| {version} | {sha} | {msg} |")

        return "\n".join(lines) + "\n"

    def update_document(self, path: Path) -> None:
        update_sentinel_section(path, _TAG, self.generate_rows())
