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

This runs pytest + coverage, validates requirement traceability, generates `docs/traceability_matrix.md`, updates the README forge health section, and exits 1 if the forge grade is below B.

Tests link to requirements with `@pytest.mark.requirement("DOMAIN-NNN")` and write structured JSON evidence via `EvidenceReport`. See `docs/Requirements_Convention.md` for the domain prefix table.

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

<!-- forge-health-start -->
*Last run: 2026-05-04*

**Grade: B** (score: 0.88)

| Collector | Score |
|-----------|-------|
| Test Metrics | 0.89 |
| Complexity | 0.68 |
| Dependency Health | 1.00 |
| Requirements Coverage | 1.00 |
| Static Analysis | 0.78 |
| Type Coverage | 0.91 |
<!-- forge-health-end -->
