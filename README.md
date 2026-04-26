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

## Forge Health

<!-- forge-health-start -->
*Last run: 2026-04-25*

**Grade: B** (score: 0.85)

| Collector | Score |
|-----------|-------|
| Test Metrics | 0.89 |
| Complexity | 0.69 |
| Dependency Health | 0.85 |
| Requirements Coverage | 1.00 |
| Static Analysis | 0.76 |
| Type Coverage | 0.91 |
<!-- forge-health-end -->
