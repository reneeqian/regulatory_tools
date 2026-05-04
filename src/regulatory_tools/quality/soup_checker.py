"""SOUP (Software of Unknown Provenance) inventory checker."""
from __future__ import annotations

import re
from pathlib import Path


def check_soup_inventory(project_root: Path) -> dict:
    """
    Verify docs/soup.yaml exists and lists all direct deps from pyproject.toml.

    Returns
    -------
    dict with keys:
        found          : bool   — True if docs/soup.yaml exists
        unlisted_deps  : list[str] — dep names in pyproject.toml not found in soup.yaml
        soup_path      : Path | None
    """
    pyproject_path = project_root / "pyproject.toml"
    soup_path = project_root / "docs" / "soup.yaml"

    result: dict = {"found": False, "unlisted_deps": [], "soup_path": None}

    if not soup_path.exists():
        return result

    result["found"] = True
    result["soup_path"] = soup_path

    # Parse dependency names from pyproject.toml
    dep_names: list[str] = []
    if pyproject_path.exists():
        text = pyproject_path.read_text()
        in_deps = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("dependencies"):
                in_deps = True
                continue
            if in_deps:
                if stripped.startswith("]"):
                    break
                # Extract package name: strip version specifiers and extras
                match = re.match(r'"?([A-Za-z0-9_\-]+)', stripped.lstrip('"'))
                if match:
                    name = match.group(1).lower().replace("-", "_").replace("_", "-")
                    dep_names.append(name)

    # Parse listed names from soup.yaml
    soup_text = soup_path.read_text().lower()
    unlisted = [
        name for name in dep_names
        if name not in soup_text
    ]
    result["unlisted_deps"] = unlisted
    return result
