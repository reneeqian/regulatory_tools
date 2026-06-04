from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from regulatory_tools.dhf.context import DHFContext
from regulatory_tools.dhf.generators.anomaly_log import AnomalyLogGenerator
from regulatory_tools.dhf.generators.baseline_register import BaselineRegisterGenerator
from regulatory_tools.dhf.generators.change_log import ChangeLogGenerator
from regulatory_tools.dhf.generators.evidence_index import EvidenceIndexGenerator
from regulatory_tools.dhf.generators.hazard_analysis import HazardAnalysisGenerator
from regulatory_tools.dhf.generators.risk_controls import RiskControlsGenerator
from regulatory_tools.dhf.generators.soup_table import SOUPTableGenerator
from regulatory_tools.dhf.generators.system_requirements import SystemRequirementsGenerator
from regulatory_tools.dhf.generators.traceability_index import TraceabilityIndexGenerator
from regulatory_tools.dhf.placeholder_filler import PlaceholderFiller
from regulatory_tools.dhf.requirements_reader import RequirementsReader
from regulatory_tools.dhf.section_scaffolder import SectionScaffolder
from regulatory_tools.dhf.validator import DHFValidator


@dataclass
class DHFGenerationReport:
    files_modified: list[Path] = field(default_factory=list)
    unfilled_vars: list[tuple[Path, str]] = field(default_factory=list)
    scaffolded_sections: list[Path] = field(default_factory=list)


class DHFGenerator:
    """Orchestrates all DHF document generation steps."""

    def __init__(self, dhf_root: Path, context: DHFContext) -> None:
        self._root = dhf_root
        self._ctx = context
        self._filler = PlaceholderFiller(context.as_placeholder_dict())

    @classmethod
    def from_config(cls, dhf_root: Path, context_file: Path) -> "DHFGenerator":
        ctx = DHFContext.from_yaml(context_file)
        DHFValidator(ctx).validate()
        return cls(dhf_root, ctx)

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------

    def fill_placeholders(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        for md_file in sorted(self._root.rglob("*.md")):
            result = self._filler.fill_file(md_file)
            if result.filled:
                report.files_modified.append(md_file)
            for var in result.unfilled:
                report.unfilled_vars.append((md_file, var))
        return report

    def update_soup_register(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        soup_path = self._ctx.data_sources.get("soup")
        if soup_path and soup_path.exists():
            gen = SOUPTableGenerator(soup_path)
            for doc in sorted(self._root.rglob("soup_register.md")):
                before = doc.read_text()
                gen.update_document(doc)
                if doc.read_text() != before:
                    report.files_modified.append(doc)
        return report

    def update_evidence_index(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        ev_dir = self._ctx.data_sources.get("evidence_runs")
        if ev_dir and ev_dir.exists():
            gen = EvidenceIndexGenerator(ev_dir)
            for doc in sorted(self._root.rglob("evidence_index.md")):
                before = doc.read_text()
                gen.update_document(doc)
                if doc.read_text() != before:
                    report.files_modified.append(doc)
        return report

    def update_system_requirements(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        req_paths = [p for p in self._ctx.requirement_paths if p.exists()]
        if req_paths:
            reader = RequirementsReader(req_paths)
            gen = SystemRequirementsGenerator(reader)
            for doc in sorted(self._root.rglob("system_requirements.md")):
                before = doc.read_text()
                gen.update_document(doc)
                if doc.read_text() != before:
                    report.files_modified.append(doc)
        return report

    def update_traceability_index(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        matrix_path = self._ctx.data_sources.get("traceability_matrix")
        if matrix_path and matrix_path.exists():
            gen = TraceabilityIndexGenerator(matrix_path)
            for doc in sorted(self._root.rglob("traceability_index.md")):
                before = doc.read_text()
                gen.update_document(doc)
                if doc.read_text() != before:
                    report.files_modified.append(doc)
        return report

    def update_risk_controls(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        req_paths = [p for p in self._ctx.requirement_paths if p.exists()]
        if req_paths:
            reader = RequirementsReader(req_paths)
            gen = RiskControlsGenerator(reader)
            for doc in sorted(self._root.rglob("risk_control_measures.md")):
                before = doc.read_text()
                gen.update_document(doc)
                if doc.read_text() != before:
                    report.files_modified.append(doc)
        return report

    def scaffold_missing_sections(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        scaffolder = SectionScaffolder(
            self._ctx.templates_root, self._root, self._filler
        )
        created = scaffolder.scaffold_missing()
        report.scaffolded_sections = created
        report.files_modified = list(created)
        return report

    def update_baseline_register(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        gen = BaselineRegisterGenerator(self._ctx.git_repo)
        for doc in sorted(self._root.rglob("baseline_register.md")):
            before = doc.read_text()
            gen.update_document(doc)
            if doc.read_text() != before:
                report.files_modified.append(doc)
        return report

    def update_change_log(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        pyproject = self._ctx.git_repo / "pyproject.toml"
        if not pyproject.exists():
            return report
        gen = ChangeLogGenerator(git_repo=self._ctx.git_repo, pyproject_toml=pyproject)
        for doc in sorted(self._root.rglob("change_log.md")):
            before = doc.read_text()
            gen.update_document(doc)
            if doc.read_text() != before:
                report.files_modified.append(doc)
        return report

    def update_hazard_analysis(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        hazard_path = self._ctx.data_sources.get("hazard_analysis")
        if hazard_path and hazard_path.exists():
            gen = HazardAnalysisGenerator(hazard_path)
            for doc in sorted(self._root.rglob("hazard_analysis.md")):
                before = doc.read_text()
                gen.update_document(doc)
                if doc.read_text() != before:
                    report.files_modified.append(doc)
        return report

    def update_anomaly_log(self) -> DHFGenerationReport:
        report = DHFGenerationReport()
        anomaly_path = self._ctx.data_sources.get("anomaly_log")
        if anomaly_path and anomaly_path.exists():
            gen = AnomalyLogGenerator(anomaly_path)
            for doc in sorted(self._root.rglob("anomaly_log.md")):
                before = doc.read_text()
                gen.update_document(doc)
                if doc.read_text() != before:
                    report.files_modified.append(doc)
        return report

    def run_all(self) -> DHFGenerationReport:
        combined = DHFGenerationReport()

        def _merge(r: DHFGenerationReport) -> None:
            combined.files_modified.extend(r.files_modified)
            combined.unfilled_vars.extend(r.unfilled_vars)
            combined.scaffolded_sections.extend(r.scaffolded_sections)

        _merge(self.scaffold_missing_sections())
        _merge(self.update_soup_register())
        _merge(self.update_evidence_index())
        _merge(self.update_system_requirements())
        _merge(self.update_traceability_index())
        _merge(self.update_risk_controls())
        _merge(self.update_hazard_analysis())
        _merge(self.update_anomaly_log())
        _merge(self.update_baseline_register())
        _merge(self.update_change_log())
        _merge(self.fill_placeholders())

        return combined
