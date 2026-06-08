"""Project status summary generator (DOC-005)."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

from regulatory_tools.quality.forge_integration import forge_health_as_dict, get_forge_health
from regulatory_tools.traceability.pipeline import generate_traceability_matrix

_MISSING = "_File not found — section unavailable._"
_COMMIT_COUNT = 4


def generate_project_summary(
    project_root: Path,
    output_path: Path | None = None,
) -> Path:
    generate_traceability_matrix(project_root)

    sections = [
        _section_header(project_root),
        _section_recent_commits(project_root),
        _section_open_issues(project_root),
        _section_forge_health(project_root),
        _section_traceability_coverage(project_root),
        _section_user_needs(project_root),
        _section_requirements_by_domain(project_root),
        _section_soup(project_root),
        _section_hazards(project_root),
        _section_anomalies(project_root),
    ]

    if output_path is None:
        output_path = project_root / "project_summary.md"

    output_path.write_text("\n\n---\n\n".join(sections) + "\n")
    return output_path


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _section_header(project_root: Path) -> str:
    req_file = project_root / "docs" / "requirements.yaml"
    if not req_file.exists():
        return "# Project Status Summary\n\n_No requirements.yaml found._"
    data = yaml.safe_load(req_file.read_text()) or {}
    meta = data.get("metadata", {})
    project = meta.get("project", "Unknown")
    samd_class = meta.get("samd_class", "—")
    version = meta.get("version", "—")
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"# Project Status Summary — {project}\n\n"
        f"**Generated:** {generated}  |  **SaMD Class:** {samd_class}  |  **Version:** {version}"
    )


def _section_recent_commits(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "log", "--format=%h %s", f"-{_COMMIT_COUNT}"],
            capture_output=True, text=True, timeout=10, cwd=project_root,
        )
        lines = [ln for ln in result.stdout.strip().splitlines() if ln]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        lines = []

    if not lines:
        return "## Recent Commits\n\n_No git history available._"

    items = "\n".join(f"- `{ln}`" for ln in lines)
    return f"## Recent Commits\n\n{items}"


def _get_remote_url(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5, cwd=project_root,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def _parse_github_slug(url: str) -> str | None:
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url.strip())
    return match.group(1) if match else None


def _section_open_issues(project_root: Path) -> str:
    remote_url = _get_remote_url(project_root)
    repo_slug = _parse_github_slug(remote_url) if remote_url else None

    if not repo_slug:
        return "## Open Issues\n\n_GitHub remote not configured._"

    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--repo", repo_slug, "--state", "open",
             "--json", "number,title,url"],
            capture_output=True, text=True, timeout=15,
        )
        issues = json.loads(result.stdout) if result.stdout.strip() else []
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return "## Open Issues\n\n_Could not fetch issues (gh CLI unavailable or not authenticated)._"

    if not issues:
        return "## Open Issues\n\n_No open issues._"

    items = "\n".join(f"- [#{i['number']} — {i['title']}]({i['url']})" for i in issues)
    return f"## Open Issues\n\n{items}"


def _section_forge_health(project_root: Path) -> str:
    report = get_forge_health(project_root)
    if report is None:
        return "## Forge Health\n\n_Forge health data unavailable._"

    summary = forge_health_as_dict(report)
    grade = summary.get("grade", "—")
    raw_score = summary.get("overall_score")
    score_str = f"{raw_score * 100:.1f}%" if raw_score is not None else "—"

    rows = []
    for name, data in summary.get("collectors", {}).items():
        label = name.replace("_", " ").title()
        if data.get("skipped"):
            rows.append(f"| {label} | — | {data.get('skip_reason', 'skipped')} |")
        else:
            s = data.get("score")
            score_display = f"{s * 100:.1f}%" if s is not None else "—"
            rows.append(f"| {label} | {score_display} | ok |")

    table = "| Collector | Score | Status |\n|---|---|---|\n" + "\n".join(rows)
    return f"## Forge Health\n\n**Grade: {grade}** ({score_str})\n\n{table}"


def _section_traceability_coverage(project_root: Path) -> str:
    rtm = project_root / "docs" / "traceability_matrix.md"
    if not rtm.exists():
        return f"## Traceability Coverage\n\n{_MISSING}"

    content = rtm.read_text()
    cov_match = re.search(r"\*\*Coverage:\*\*\s*([\d.]+%\s*\([^)]+\))", content)
    line_match = re.search(r"\*\*Line Coverage:\*\*\s*([\d.]+%)", content)
    cov_str = cov_match.group(1) if cov_match else "—"
    line_str = line_match.group(1) if line_match else "—"

    return (
        f"## Traceability Coverage\n\n"
        f"- Requirements: {cov_str}\n"
        f"- Code coverage: {line_str}\n\n"
        f"_(Full matrix: docs/traceability_matrix.md)_"
    )


def _section_user_needs(project_root: Path) -> str:
    un_file = project_root / "docs" / "user_needs.yaml"
    if not un_file.exists():
        return f"## User Needs\n\n{_MISSING}"

    data = yaml.safe_load(un_file.read_text()) or {}
    reqs = data.get("requirements", [])
    if not reqs:
        return "## User Needs\n\n_No user needs defined._"

    rows = [
        f"| {r.get('id','—')} | {r.get('title','—')} | {r.get('intended_user','—')} | {r.get('verification_method','—')} |"
        for r in reqs
    ]
    table = "| ID | Title | Intended User | Verification |\n|---|---|---|---|\n" + "\n".join(rows)
    return f"## User Needs\n\n{table}"


def _section_requirements_by_domain(project_root: Path) -> str:
    docs = project_root / "docs"
    all_reqs: list[dict] = []
    for fname in ("requirements.yaml", "design.yaml", "risk_controls.yaml"):
        f = docs / fname
        if f.exists():
            data = yaml.safe_load(f.read_text()) or {}
            all_reqs.extend(data.get("requirements", []))

    if not all_reqs:
        return f"## Requirements by Domain\n\n{_MISSING}"

    counts: dict[str, int] = {}
    for r in all_reqs:
        prefix = r.get("id", "?").split("-")[0]
        counts[prefix] = counts.get(prefix, 0) + 1

    rows = [f"| {prefix} | {count} |" for prefix, count in sorted(counts.items())]
    table = "| Prefix | Count |\n|---|---|\n" + "\n".join(rows)
    return (
        f"## Requirements by Domain\n\n{table}\n\n"
        f"_(Per-requirement status: docs/traceability_matrix.md)_"
    )


def _section_soup(project_root: Path) -> str:
    soup_file = project_root / "docs" / "soup.yaml"
    if not soup_file.exists():
        return f"## SOUP\n\n{_MISSING}"

    data = yaml.safe_load(soup_file.read_text()) or {}
    entries = data.get("soup", [])
    if not entries:
        return "## SOUP\n\n_No SOUP entries._"

    rows = [
        f"| {e.get('name','—')} | {e.get('version','—')} | {e.get('intended_use', e.get('purpose','—'))} | {e.get('risk','—')} | {e.get('verified_by','—')} |"
        for e in entries
    ]
    table = "| Name | Version | Intended Use | Risk | Verified By |\n|---|---|---|---|---|\n" + "\n".join(rows)
    return f"## SOUP\n\n{table}"


def _section_hazards(project_root: Path) -> str:
    haz_file = project_root / "docs" / "hazard_analysis.yaml"
    if not haz_file.exists():
        return f"## Hazards\n\n{_MISSING}"

    data = yaml.safe_load(haz_file.read_text()) or {}
    hazards = data.get("hazards", [])
    if not hazards:
        return "## Hazards\n\n_No hazards defined._"

    rows = [
        f"| {h.get('id','—')} | {h.get('hazard','—')} | {h.get('severity','—')} | {h.get('probability','—')} | {h.get('mitigation_ref','—')} |"
        for h in hazards
    ]
    table = "| ID | Hazard | Severity | Probability | Mitigation |\n|---|---|---|---|---|\n" + "\n".join(rows)
    return f"## Hazards\n\n{table}"


def _section_anomalies(project_root: Path) -> str:
    anom_file = project_root / "docs" / "anomaly_log.yaml"
    if not anom_file.exists():
        return f"## Anomalies\n\n{_MISSING}"

    data = yaml.safe_load(anom_file.read_text()) or {}
    anomalies = data.get("anomalies", [])
    open_anoms = [a for a in anomalies if str(a.get("status", "")).lower() != "resolved"]

    if not open_anoms:
        return "## Anomalies\n\nNo open anomalies."

    rows = [
        f"| {a.get('id','—')} | {a.get('title','—')} | {a.get('status','—')} | {a.get('priority', a.get('severity','—'))} |"
        for a in open_anoms
    ]
    table = "| ID | Title | Status | Priority |\n|---|---|---|---|\n" + "\n".join(rows)
    return f"## Anomalies\n\n{table}"
