# Regulatory Tools

Automation infrastructure for generating structured, traceable,
machine-derived regulatory artifacts for SaMD projects.

---

## Purpose

This repository provides tooling for:

- requirement validation
- test linkage
- evidence aggregation
- traceability matrix generation
- code coverage reporting

The objective is deterministic, machine-generated regulatory documentation.

---

## Example Usage

Projects typically run:

```python
from regulatory_tools.testing import run_tests_and_trace

run_tests_and_trace(PROJECT_ROOT)
```

Which will:

1. run pytest
2. compute coverage
3. validate traceability
4. generate a traceability matrix

---

## Structure

```
regulatory_tools/
├── src/regulatory_tools/
│ ├── testing/
│ ├── traceability/
│ └── evidence/
├── tests/
├── environment.yml
└── README.md
```

---

Demonstration infrastructure only.
Not an FDA submission package.

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
