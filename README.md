# Regulatory Tools

Automation infrastructure for machine-generated regulatory artifacts: requirement traceability, evidence reports, and coverage for SaMD demonstration projects.

Not an FDA submission package — engineering demonstration only.

## Install

```bash
pip install -e .
```

## Usage

Projects call `run_tests_and_trace` as their verification entry point:

```python
from regulatory_tools.testing import run_tests_and_trace

run_tests_and_trace(project_root=Path(__file__).resolve().parent)
```

This runs pytest + coverage, validates requirement traceability, generates `docs/traceability_matrix.md`, and exits 1 if the forge grade is below B. The forge health report is written to the GitHub Actions job summary — visible in the Checks tab of every PR. Running locally writes the report to README.md between the markers below (local only, not committed).

Tests link to requirements with `@pytest.mark.requirement("DOMAIN-NNN")` and write structured JSON evidence via `EvidenceReport`. See `docs/Requirements_Convention.md` for the domain prefix table.

---

## Project Status Summary

Generate a single Markdown snapshot of a project's current state — useful for re-orienting after time away:

```bash
regulatory-summary <project_root>
# or
python -m regulatory_tools.summary <project_root>
```

Writes `<project_root>/project_summary.md` (git-ignored by convention). The command regenerates `docs/traceability_matrix.md` first so all stats are current.

**Output sections:**

| Section | Source |
|---|---|
| Project header (name, SaMD class, version) | `docs/requirements.yaml` metadata |
| Recent commits (last 4) | `git log` |
| Open GitHub issues with hyperlinks | `gh issue list` |
| Forge health (grade, score, per-collector) | forge via `get_forge_health()` |
| Traceability coverage (requirements %, line coverage %) | freshly-written `docs/traceability_matrix.md` |
| User needs table | `docs/user_needs.yaml` |
| Requirements by domain (count per prefix) | `docs/requirements.yaml` + `design.yaml` + `risk_controls.yaml` |
| SOUP inventory | `docs/soup.yaml` |
| Hazard summary | `docs/hazard_analysis.yaml` |
| Anomalies (open only) | `docs/anomaly_log.yaml` |

Optional files (SOUP, hazards, user needs, anomalies) degrade gracefully if absent. The `gh` CLI is optional — its section falls back to a note if unavailable.

---

## GitHub Repository Setup

`scripts/setup_github_settings.sh` applies the standard safe CI/CD configuration to any new GitHub repo. Run it once after creating a repo:

```bash
./scripts/setup_github_settings.sh <owner/repo>
# e.g.
./scripts/setup_github_settings.sh reneeqian/my_new_samd_project
```

What it configures:

- **`main`** — PR required, 1 review + code owner approval, strict CI (`test` + `forge-health` must pass on an up-to-date branch), merge commit only, stale reviews dismissed on push, no force-push or deletion
- **`dev`** — PR required (no approval), CI required, squash merge only, no force-push or deletion
- **Repo** — rebase merge disabled, auto-delete feature branches on merge, auto-merge capability enabled

The script is idempotent — safe to re-run. The one manual step is committing `.github/CODEOWNERS` (the script prints the exact commands). Custom CI job names can be passed as arguments — see the script header for full usage.

---

## Forge Health

Latest report: see the [Actions tab](../../actions) or the job summary on any PR's Checks tab.

<!-- forge-health-start -->
*Last run: 2026-06-08*

**Grade: B** (score: 0.84)

| Collector | Score |
|-----------|-------|
| Test Metrics | 0.89 |
| Complexity | 0.66 |
| Dependency Health | 0.70 |
| Requirements Coverage | 1.00 |
| Static Analysis | 0.94 |
| Type Coverage | 0.95 |
| Dead Code | 1.00 |
<!-- forge-health-end -->
