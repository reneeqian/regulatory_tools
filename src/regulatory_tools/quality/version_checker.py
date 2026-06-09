"""Version baseline consistency checker — VER-009."""

from __future__ import annotations

import subprocess
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


def _get_latest_tag(project_root: Path) -> str | None:
    """Return the latest git tag (e.g. 'v1.1.0') or None if no tags exist."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    tag = result.stdout.strip()
    return tag if result.returncode == 0 and tag else None


def check_version_baseline(project_root: Path) -> dict:
    """
    Verify that pyproject.toml [project] version matches the latest git tag.

    Returns
    -------
    dict with keys:
        found             : bool       — True if pyproject.toml exists
        has_tags          : bool       — True if any git tags were found
        pyproject_version : str | None — version from pyproject.toml
        latest_tag        : str | None — latest tag stripped of leading 'v'
        match             : bool       — True if versions agree
        violations        : list[str]  — non-empty when tags exist but version mismatches
        warning           : str | None — set when no tags exist (not a violation)
    """
    pyproject_path = project_root / "pyproject.toml"
    result: dict = {
        "found": False,
        "has_tags": False,
        "pyproject_version": None,
        "latest_tag": None,
        "match": False,
        "violations": [],
        "warning": None,
    }

    if not pyproject_path.exists():
        return result

    result["found"] = True
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    version = pyproject.get("project", {}).get("version")
    result["pyproject_version"] = version

    raw_tag = _get_latest_tag(project_root)
    if raw_tag is None:
        result["warning"] = "No git tags found — version baseline cannot be verified"
        return result

    result["has_tags"] = True
    tag_version = raw_tag.lstrip("v")
    result["latest_tag"] = tag_version

    if version == tag_version:
        result["match"] = True
    else:
        result["violations"].append(
            f"pyproject.toml version '{version}' does not match latest git tag '{tag_version}'"
        )

    return result
