from __future__ import annotations

import re
from pathlib import Path


def update_sentinel_section(path: Path, tag: str, rows: str) -> None:
    """Replace the content between <!-- DHF_{tag}_START/END --> in a file."""
    content = path.read_text()
    pattern = re.compile(
        rf"(<!-- DHF_{tag}_START -->\n)(.*?)(<!-- DHF_{tag}_END -->)",
        re.DOTALL,
    )
    new_content = pattern.sub(rf"\g<1>{rows}\g<3>", content)
    if new_content != content:
        path.write_text(new_content)
