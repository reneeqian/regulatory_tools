from __future__ import annotations

from pathlib import Path

import yaml

from regulatory_tools.dhf.requirements_reader import RequirementsReader, _load_all


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
        for req_path in self._ctx.requirement_paths:
            if not req_path.exists():
                violations.append(f"Missing required file 'requirements': {req_path}")

        soup = self._ctx.data_sources.get("soup")
        if soup is None or not Path(soup).exists():
            violations.append(f"Missing required file 'soup': {soup}")

        tm = self._ctx.data_sources.get("traceability_matrix")
        if tm is None or not Path(tm).exists():
            violations.append(f"Missing required file 'traceability_matrix': {tm}")

        evidence_dir = self._ctx.data_sources.get("evidence_runs")
        if evidence_dir is None or not Path(evidence_dir).is_dir():
            violations.append(f"Missing or not-a-directory 'evidence_runs': {evidence_dir}")

        if not self._ctx.templates_root.exists():
            violations.append(f"templates_root does not exist: {self._ctx.templates_root}")

    def _check_requirements(self, violations: list[str]) -> None:
        req_paths = [p for p in self._ctx.requirement_paths if p.exists()]
        if not req_paths:
            return  # file-existence already reported in _check_files

        try:
            reqs, file_metadata = _load_all(req_paths)
        except ValueError as exc:
            violations.append(f"requirements could not be parsed: {exc}")
            return
        except Exception as exc:
            violations.append(f"requirements could not be parsed: {exc}")
            return

        # Duplicate IDs (can only arise across files now — within-file duplicates are caught by _load_all)
        seen_ids: set[str] = set()
        for r in reqs:
            if r.id in seen_ids:
                violations.append(f"Duplicate requirement id: '{r.id}'")
            seen_ids.add(r.id)

        # Per-file constraint checks (DHF-011, DHF-013) — only for files with metadata constraints
        for stem, meta in file_metadata.items():
            constrained = "allowed_prefixes" in meta or "allowed_types" in meta
            if not constrained:
                continue  # old-format file; skip constraint checks

            # DHF-013: file_role required when constraints are declared
            if "file_role" not in meta:
                violations.append(
                    f"{stem}.yaml declares allowed_prefixes/allowed_types but is missing metadata.file_role"
                )

            allowed_prefixes: list[str] = meta.get("allowed_prefixes", [])
            allowed_types: list[str] = meta.get("allowed_types", [])

            for r in reqs:
                if r.source_file != stem:
                    continue

                # DHF-013: prefix check
                if allowed_prefixes:
                    prefix = r.id.split("-")[0]
                    if prefix not in allowed_prefixes:
                        violations.append(
                            f"{stem}.yaml: requirement '{r.id}' has prefix '{prefix}' "
                            f"not in allowed_prefixes {allowed_prefixes}"
                        )

                # DHF-013: type check
                if allowed_types and r.type not in allowed_types:
                    violations.append(
                        f"{stem}.yaml: requirement '{r.id}' has type '{r.type}' "
                        f"not in allowed_types {allowed_types}"
                    )

                # DHF-011: derived_from completeness (non-user_need in constrained file)
                if r.type != "user_need" and not r.derived_from:
                    violations.append(
                        f"requirement '{r.id}' (type={r.type!r}) has no derived_from — "
                        f"every non-user_need requirement must trace to a parent"
                    )
