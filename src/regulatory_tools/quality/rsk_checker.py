"""Risk-requirement (RSK-) presence checker."""
from __future__ import annotations

import re
from pathlib import Path


def check_rsk_requirements(project_root: Path) -> dict:
    """
    Check docs/requirements.yaml for at least one RSK- prefixed requirement.

    Returns
    -------
    dict with keys:
        found    : bool       — True if at least one RSK- requirement exists
        rsk_ids  : list[str]  — all RSK- IDs found
    """
    req_path = project_root / "docs" / "requirements.yaml"
    result: dict = {"found": False, "rsk_ids": []}

    if not req_path.exists():
        return result

    text = req_path.read_text()
    rsk_ids = re.findall(r"\bRSK-\d+\b", text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_ids = [x for x in rsk_ids if not (x in seen or seen.add(x))]  # type: ignore[func-returns-value]

    result["found"] = bool(unique_ids)
    result["rsk_ids"] = unique_ids
    return result
