from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import yaml

_VALID_TYPES: frozenset[str] = frozenset(
    {"user_need", "system_requirement", "design_requirement", "risk_control"}
)
_DEFAULT_TYPE = "system_requirement"


@dataclass
class Requirement:
    id: str
    type: str
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)


class RequirementsReader:
    """Parses requirements.yaml into typed Requirement objects."""

    def __init__(self, path: Path) -> None:
        self._requirements: list[Requirement] = self.load(path)

    @staticmethod
    def load(path: Path) -> list[Requirement]:
        with open(path) as f:
            data = yaml.safe_load(f)

        result: list[Requirement] = []
        for entry in data.get("requirements", []):
            req_type = entry.get("type", _DEFAULT_TYPE)
            if req_type not in _VALID_TYPES:
                raise ValueError(
                    f"Requirement {entry.get('id')!r} has unknown type {req_type!r}. "
                    f"Valid types: {sorted(_VALID_TYPES)}"
                )
            result.append(
                Requirement(
                    id=entry["id"],
                    type=req_type,
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    tags=entry.get("tags", []),
                    derived_from=entry.get("derived_from", []),
                )
            )
        return result

    def by_type(self, type_str: str) -> list[Requirement]:
        return [r for r in self._requirements if r.type == type_str]

    def derived_from_id(self, req_id: str) -> list[Requirement]:
        return [r for r in self._requirements if req_id in r.derived_from]

    def all(self) -> list[Requirement]:
        return list(self._requirements)
