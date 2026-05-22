from __future__ import annotations

from pathlib import Path

import yaml

from regulatory_tools.dhf.requirements_reader import RequirementsReader


class DHFValidationError(Exception):
    """Raised when DHF input files fail contract validation."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__("\n".join(f"  - {v}" for v in violations))


class DHFValidator:
    """Validates all DHF input sources before generation begins."""

    def __init__(self, context: "DHFContext") -> None:  # type: ignore[name-defined]
        self._ctx = context

    def validate(self) -> None:
        violations: list[str] = []
        self._check_files(violations)
        self._check_requirements(violations)
        if violations:
            raise DHFValidationError(violations)

    def _check_files(self, violations: list[str]) -> None:
        checks = {
            "soup": self._ctx.data_sources.get("soup"),
            "requirements": self._ctx.data_sources.get("requirements"),
            "traceability_matrix": self._ctx.data_sources.get("traceability_matrix"),
        }
        for label, path in checks.items():
            if path is None or not Path(path).exists():
                violations.append(f"Missing required file '{label}': {path}")

        evidence_dir = self._ctx.data_sources.get("evidence_runs")
        if evidence_dir is None or not Path(evidence_dir).is_dir():
            violations.append(f"Missing or not-a-directory 'evidence_runs': {evidence_dir}")

        if not self._ctx.templates_root.exists():
            violations.append(f"templates_root does not exist: {self._ctx.templates_root}")

    def _check_requirements(self, violations: list[str]) -> None:
        reqs_path = self._ctx.data_sources.get("requirements")
        if reqs_path is None or not Path(reqs_path).exists():
            return  # already reported in _check_files

        try:
            reqs = RequirementsReader.load(Path(reqs_path))
        except Exception as exc:
            violations.append(f"requirements.yaml could not be parsed: {exc}")
            return

        seen_ids: set[str] = set()
        for r in reqs:
            if r.id in seen_ids:
                violations.append(f"requirements.yaml has duplicate id: '{r.id}'")
            seen_ids.add(r.id)
