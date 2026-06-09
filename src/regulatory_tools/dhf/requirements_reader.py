from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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
    source_file: str = field(default="")


class RequirementsReader:
    """Parses one or more requirements YAML files into typed Requirement objects."""

    def __init__(self, paths: Path | list[Path]) -> None:
        if isinstance(paths, Path):
            paths = [paths]
        self._requirements, self._file_metadata = _load_all(paths)

    @staticmethod
    def load(path: Path) -> list[Requirement]:
        """Load a single file. Sets source_file to path.stem on each Requirement."""
        return _load_file(path)

    @property
    def file_metadata(self) -> dict[str, dict]:
        """Metadata dicts keyed by filename stem, e.g. {'requirements': {...}, 'design': {...}}."""
        return self._file_metadata

    def by_type(self, type_str: str) -> list[Requirement]:
        return [r for r in self._requirements if r.type == type_str]

    def derived_from_id(self, req_id: str) -> list[Requirement]:
        return [r for r in self._requirements if req_id in r.derived_from]

    def all(self) -> list[Requirement]:
        return list(self._requirements)


def _load_file(path: Path) -> list[Requirement]:
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
                source_file=path.stem,
            )
        )
    return result


def _load_all(paths: list[Path]) -> tuple[list[Requirement], dict[str, dict]]:
    all_reqs: list[Requirement] = []
    seen_ids: set[str] = set()
    file_metadata: dict[str, dict] = {}

    for path in paths:
        with open(path) as f:
            data = yaml.safe_load(f)
        file_metadata[path.stem] = data.get("metadata", {})

        for entry in data.get("requirements", []):
            req_id = entry["id"]
            if req_id in seen_ids:
                raise ValueError(f"Duplicate requirement ID across files: {req_id!r}")
            seen_ids.add(req_id)

            req_type = entry.get("type", _DEFAULT_TYPE)
            if req_type not in _VALID_TYPES:
                raise ValueError(
                    f"Requirement {req_id!r} has unknown type {req_type!r}. "
                    f"Valid types: {sorted(_VALID_TYPES)}"
                )
            all_reqs.append(
                Requirement(
                    id=req_id,
                    type=req_type,
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    tags=entry.get("tags", []),
                    derived_from=entry.get("derived_from", []),
                    source_file=path.stem,
                )
            )

    return all_reqs, file_metadata
