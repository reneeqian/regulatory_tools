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
