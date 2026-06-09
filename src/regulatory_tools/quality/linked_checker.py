"""LINKED requirements gate checker — VER-011."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REGULATED_CLASSES = {"a", "b", "c", "tool"}


def _read_samd_class(project_root: Path) -> str:
    req_path = project_root / "docs" / "requirements.yaml"
    if not req_path.exists():
        return ""
    with open(req_path) as f:
        data = yaml.safe_load(f)
    return str(data.get("metadata", {}).get("samd_class", "")).lower()


def check_linked_requirements(project_root: Path) -> dict:
    """
    Read docs/traceability_matrix.md and return IDs of LINKED requirements.

    For samd_class utility the check is skipped and linked_ids is always [].

    Returns
    -------
    dict with keys:
        linked_ids : list[str] — requirement IDs with LINKED status
        samd_class : str       — value read from docs/requirements.yaml metadata
        skipped    : bool      — True if check does not apply (utility class)
    """
    samd_class = _read_samd_class(project_root)
    result: dict = {"linked_ids": [], "samd_class": samd_class, "skipped": False}

    if samd_class not in _REGULATED_CLASSES:
        result["skipped"] = True
        return result

    rtm_path = project_root / "docs" / "traceability_matrix.md"
    if not rtm_path.exists():
        return result

    linked: list[str] = []
    for line in rtm_path.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if not cells:
            continue
        # Status is the last cell; requirement ID is the first cell
        if cells[-1] == "LINKED":
            req_id = cells[0]
            # Skip header and separator rows
            if re.match(r"^[A-Z]{2,6}-\d+$", req_id):
                linked.append(req_id)

    result["linked_ids"] = linked
    return result
