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

## Forge Health

Latest report: see the [Actions tab](../../actions) or the job summary on any PR's Checks tab.

<!-- forge-health-start -->
<!-- forge-health-end -->
