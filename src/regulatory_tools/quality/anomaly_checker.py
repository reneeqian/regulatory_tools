"""Anomaly log existence checker — VER-010."""
from __future__ import annotations

from pathlib import Path

import yaml

_REGULATED_CLASSES = {"a", "b", "c", "tool"}


def _read_samd_class(project_root: Path) -> str | None:
    req_path = project_root / "docs" / "requirements.yaml"
    if not req_path.exists():
        return None
    with open(req_path) as f:
        data = yaml.safe_load(f)
    return str(data.get("metadata", {}).get("samd_class", "")).lower()


def check_anomaly_log(project_root: Path) -> dict:
    """
    Verify that docs/anomaly_log.yaml exists for regulated packages.

    Packages with samd_class 'utility' are skipped.

    Returns
    -------
    dict with keys:
        found      : bool      — True if docs/anomaly_log.yaml exists
        skipped    : bool      — True if check does not apply (utility class)
        samd_class : str       — value read from docs/requirements.yaml metadata
        violations : list[str] — non-empty when anomaly log is absent and required
    """
    samd_class = _read_samd_class(project_root) or ""
    result: dict = {
        "found": False,
        "skipped": False,
        "samd_class": samd_class,
        "violations": [],
    }

    if samd_class not in _REGULATED_CLASSES:
        result["skipped"] = True
        return result

    anomaly_path = project_root / "docs" / "anomaly_log.yaml"
    if anomaly_path.exists():
        result["found"] = True
    else:
        result["violations"].append(
            "docs/anomaly_log.yaml absent — IEC 62304 §9.1 requires a formal problem resolution record"
        )

    return result
