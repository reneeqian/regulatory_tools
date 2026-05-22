from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_SENTINEL_RE = re.compile(
    r"<!-- DHF_VAR:([A-Z_]+) -->(.*?)<!-- /DHF_VAR:\1 -->",
    re.DOTALL,
)
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def _sentinel(name: str, value: str) -> str:
    return f"<!-- DHF_VAR:{name} -->{value}<!-- /DHF_VAR:{name} -->"


@dataclass
class FilledResult:
    content: str
    filled: list[str] = field(default_factory=list)
    unfilled: list[str] = field(default_factory=list)


class PlaceholderFiller:
    """
    Fills {{VAR_NAME}} placeholders and updates previously-filled sentinel values.

    First run:  {{PROJECT_NAME}} → <!-- DHF_VAR:PROJECT_NAME -->COCA-prj<!-- /DHF_VAR:PROJECT_NAME -->
    Re-run:     sentinel is updated in place when the context value changes.
    Manual fills (no sentinel) are never touched.
    """

    def __init__(self, context: dict[str, str]) -> None:
        self._context = context

    def fill(self, content: str) -> FilledResult:
        filled: list[str] = []
        unfilled: list[str] = []

        # Pass 1: update existing sentinel-wrapped values
        def _update_sentinel(m: re.Match) -> str:
            name = m.group(1)
            if name in self._context:
                new_value = self._context[name]
                if new_value != m.group(2):
                    filled.append(name)
                return _sentinel(name, new_value)
            return m.group(0)  # unknown sentinel — leave unchanged

        content = _SENTINEL_RE.sub(_update_sentinel, content)

        # Pass 2: replace remaining {{VAR}} placeholders
        def _fill_placeholder(m: re.Match) -> str:
            name = m.group(1)
            if name in self._context:
                filled.append(name)
                return _sentinel(name, self._context[name])
            unfilled.append(name)
            return m.group(0)

        content = _PLACEHOLDER_RE.sub(_fill_placeholder, content)

        return FilledResult(content=content, filled=filled, unfilled=unfilled)

    def fill_file(self, path: Path) -> FilledResult:
        original = path.read_text()
        result = self.fill(original)
        if result.content != original:
            path.write_text(result.content)
        return result
