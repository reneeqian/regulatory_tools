from __future__ import annotations

import shutil
from pathlib import Path

from regulatory_tools.dhf.placeholder_filler import PlaceholderFiller


class SectionScaffolder:
    """Copies missing DHF sections from a templates directory and fills placeholders."""

    def __init__(
        self,
        templates_root: Path,
        dhf_root: Path,
        filler: PlaceholderFiller,
    ) -> None:
        self._templates = templates_root
        self._dhf = dhf_root
        self._filler = filler

    def scaffold_missing(self) -> list[Path]:
        created: list[Path] = []
        for section_dir in sorted(self._templates.iterdir()):
            if not section_dir.is_dir():
                continue
            target_dir = self._dhf / section_dir.name
            if target_dir.exists():
                continue
            target_dir.mkdir(parents=True)
            for src_file in sorted(section_dir.iterdir()):
                if not src_file.is_file():
                    continue
                dest = target_dir / src_file.name
                shutil.copy2(src_file, dest)
                self._filler.fill_file(dest)
                created.append(dest)
        return created
