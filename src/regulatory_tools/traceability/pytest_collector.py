import subprocess
from typing import Dict, List

def collect_test_requirements() -> Dict[str, List[str]]:
    """
    Returns:
        {
          "test_ct_volume_structure_and_spacing": ["CAC-DR-01", "CAC-DR-02"]
        }
    """
    result = subprocess.run(
        ["pytest", "--collect-only", "-q", "--disable-warnings"],
        capture_output=True,
        text=True,
        check=True,
    )

    mapping: Dict[str, List[str]] = {}

    for line in result.stdout.splitlines():
        if "::" not in line:
            continue

        test_id = line.split("::")[-1]

        # Pytest does not expose markers here; this is a stub for v1
        mapping.setdefault(test_id, [])

    return mapping
