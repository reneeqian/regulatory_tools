"""Risk-requirement (RSK-) presence checker."""
from __future__ import annotations

import re
from pathlib import Path


_REQUIREMENT_FILE_NAMES = [
    "user_needs.yaml",
    "requirements.yaml",
    "design.yaml",
    "risk_controls.yaml",
]


def check_rsk_requirements(project_root: Path) -> dict:
    """
    Check all known requirement files in docs/ for RSK- prefixed requirements.

    Scans user_needs.yaml, requirements.yaml, design.yaml, and risk_controls.yaml
    (whichever exist), matching the 5-file split convention.

    Returns
    -------
    dict with keys:
        found    : bool       — True if at least one RSK- requirement exists
        rsk_ids  : list[str]  — all unique RSK- IDs found across all files
    """
    docs_dir = project_root / "docs"
    result: dict = {"found": False, "rsk_ids": []}

    seen: set[str] = set()
    unique_ids: list[str] = []

    for name in _REQUIREMENT_FILE_NAMES:
        path = docs_dir / name
        if not path.exists():
            continue
        for rsk_id in re.findall(r"\bRSK-\d+\b", path.read_text()):
            if rsk_id not in seen:
                seen.add(rsk_id)
                unique_ids.append(rsk_id)

    result["found"] = bool(unique_ids)
    result["rsk_ids"] = unique_ids
    return result
