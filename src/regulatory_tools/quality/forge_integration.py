"""Optional forge integration for regulatory_tools.

forge is NOT a hard dependency. All functions degrade gracefully when forge is
not installed — the regulatory pipeline continues working without it.

When forge IS available, `get_forge_health()` runs forge's full collector suite
against a project (in coverage-only mode to avoid re-running tests that
regulatory_tools already ran), and `forge_health_as_dict()` serialises the
result into a plain dict for use by the traceability generator.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forge.models import ProjectHealthReport

_FORGE_AVAILABLE: bool | None = None  # cached after first import attempt


def _try_import_forge() -> bool:
    """Return True if forge's Aggregator can be imported."""
    global _FORGE_AVAILABLE
    if _FORGE_AVAILABLE is not None:
        return _FORGE_AVAILABLE
    try:
        from forge.aggregator import Aggregator  # noqa: F401
        _FORGE_AVAILABLE = True
    except ImportError:
        _FORGE_AVAILABLE = False
    return _FORGE_AVAILABLE


def get_forge_health(project_root: Path) -> "ProjectHealthReport | None":
    """Run forge's collector suite against *project_root*.

    Uses skip_test_run=True so forge reads the coverage report produced by
    regulatory_tools' own pytest run rather than executing tests again.

    Returns None when forge is not installed or when collection fails for any
    reason — callers must handle None gracefully.
    """
    if not _try_import_forge():
        return None
    try:
        from forge.aggregator import Aggregator
        return Aggregator().run(project_root, skip_test_run=True)
    except Exception as exc:
        print(f"[forge_integration] forge health check failed: {exc}")
        return None


def forge_health_as_dict(report: "ProjectHealthReport") -> dict:
    """Serialise a ProjectHealthReport to a plain dict.

    Keeps generator.py free of forge type imports — all forge types stay
    inside this module behind the TYPE_CHECKING guard.
    """
    collector_keys = (
        "test_metrics",
        "complexity",
        "dependency_health",
        "requirements_coverage",
        "static_analysis",
        "type_coverage",
        "dead_code",
        "mutation_testing",
    )
    collectors: dict[str, dict] = {}
    for key in collector_keys:
        result = getattr(report, key, None)
        if result is None:
            continue
        collectors[key] = {
            "score": result.score,
            "skipped": result.skipped,
            "skip_reason": result.skip_reason,
        }

    overall = report.overall_score
    return {
        "project_name": report.project_name,
        "overall_score": overall,
        "grade": report.grade,
        "generated_at": report.generated_at.isoformat(),
        "collectors": collectors,
    }


_COLLECTOR_DISPLAY_NAMES: dict[str, str] = {
    "test_metrics": "Test Metrics",
    "complexity": "Complexity",
    "dependency_health": "Dependency Health",
    "requirements_coverage": "Requirements Coverage",
    "static_analysis": "Static Analysis",
    "type_coverage": "Type Coverage",
    "dead_code": "Dead Code",
    "mutation_testing": "Mutation Testing",
}

_README_START = "<!-- forge-health-start -->"
_README_END = "<!-- forge-health-end -->"


def update_readme_forge_health(project_root: Path, forge_summary: dict) -> None:
    """Write/replace the forge health section in README.md.

    Replaces content between <!-- forge-health-start --> and <!-- forge-health-end -->.
    If the markers are absent, appends a new ## Forge Health section.
    """
    readme_path = project_root / "README.md"
    if not readme_path.exists():
        return

    grade = forge_summary.get("grade", "N/A")
    overall = forge_summary.get("overall_score")
    generated_at = forge_summary.get("generated_at", "")[:10]  # YYYY-MM-DD

    score_display = f"{overall:.2f}" if overall is not None else "N/A"

    rows = []
    for key, display in _COLLECTOR_DISPLAY_NAMES.items():
        c = forge_summary.get("collectors", {}).get(key)
        if c is None or c.get("skipped"):
            continue
        score = c.get("score")
        rows.append(f"| {display} | {score:.2f} |" if score is not None else f"| {display} | N/A |")

    table = "\n".join(["| Collector | Score |", "|-----------|-------|"] + rows) if rows else ""

    block = (
        f"*Last run: {generated_at}*\n\n"
        f"**Grade: {grade}** (score: {score_display})\n\n"
        f"{table}"
    )

    report_section = f"{_README_START}\n{block}\n{_README_END}"

    text = readme_path.read_text()
    if _README_START in text and _README_END in text:
        before = text[: text.index(_README_START)]
        after = text[text.index(_README_END) + len(_README_END) :]
        text = before + report_section + after
    else:
        text = text.rstrip("\n") + f"\n\n## Forge Health\n\n{report_section}\n"

    readme_path.write_text(text)
