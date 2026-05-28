from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from regulatory_tools.dhf.validator import DHFValidationError

_REQUIRED_FIELDS = ("project_name", "responsible_person", "code_repos", "author",
                    "data_sources", "templates_root", "git_repo")
_REQUIRED_DATA_SOURCES = ("soup", "evidence_runs", "requirements", "traceability_matrix")


@dataclass
class DHFContext:
    project_name: str
    responsible_person: str
    code_repos: list[str]
    author: str
    data_sources: dict[str, Any]
    templates_root: Path
    git_repo: Path

    @property
    def requirement_paths(self) -> list[Path]:
        """Normalize requirements entry (string or list) to a list of Paths."""
        r = self.data_sources.get("requirements")
        if r is None:
            return []
        if isinstance(r, list):
            return [Path(p) for p in r]
        return [Path(r)]

    @staticmethod
    def from_yaml(path: Path) -> "DHFContext":
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise DHFValidationError([f"dhf_context.yaml is not valid YAML: {exc}"])

        violations: list[str] = []
        for key in _REQUIRED_FIELDS:
            if key not in data:
                violations.append(f"dhf_context.yaml is missing required field: '{key}'")
        if violations:
            raise DHFValidationError(violations)

        ds_raw = data["data_sources"]
        for ds_key in _REQUIRED_DATA_SOURCES:
            if ds_key not in ds_raw:
                violations.append(f"dhf_context.yaml data_sources missing key: '{ds_key}'")
        if violations:
            raise DHFValidationError(violations)

        data_sources: dict[str, Any] = {}
        for k, v in ds_raw.items():
            if k == "requirements" and isinstance(v, list):
                data_sources[k] = [str(p) for p in v]
            else:
                data_sources[k] = Path(v)

        return DHFContext(
            project_name=data["project_name"],
            responsible_person=data["responsible_person"],
            code_repos=list(data["code_repos"]),
            author=data["author"],
            data_sources=data_sources,
            templates_root=Path(data["templates_root"]),
            git_repo=Path(data["git_repo"]),
        )

    def as_placeholder_dict(self) -> dict[str, str]:
        return {
            "PROJECT_NAME": self.project_name,
            "RESPONSIBLE_PERSON": self.responsible_person,
            "AUTHOR": self.author,
            "CODE_REPO": ", ".join(self.code_repos),
        }
