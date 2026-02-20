# Requirements Identification Convention

## Purpose

This document defines the standardized requirement identification
and formatting convention used across regulated AI demonstration projects.

This convention supports:

- Stable traceability
- Automated matrix generation
- Cross-repository consistency
- Scalable requirement growth

---

## Requirement ID Format

All requirements shall follow the format:

```
<DOMAIN>-<NNN>
```

Where:

- `<DOMAIN>` is a predefined category prefix
- `<NNN>` is a zero-padded three-digit number (001–999)

Example:

```
SYS-001
DATA-003
TRN-002
VER-001
```


---

## Domain Prefix Definitions

| Prefix | Domain | Description |
|--------|--------|------------|
| SYS | System | High-level system behavior requirements |
| DAT | Data | Data ingestion, validation, and access requirements |
| TRN | Training | Model training process requirements |
| MOD | Model | Model architecture and initialization requirements |
| INF | Infrastructure | Pipeline orchestration and runtime behavior |
| VER | Verification | Test execution and evidence generation requirements |
| RSK | Risk | Risk control and mitigation requirements |
| DOC | Documentation | Documentation and traceability control requirements |

---

## Requirement Authoring Rules

1. Requirements shall describe **what must be true**, not how it is implemented.
2. Requirements shall avoid referencing:
   - Specific class names
   - Specific file paths
   - Specific test names
   - Specific libraries
3. Requirements shall be implementation-agnostic.
4. Requirement IDs shall never be reused.
5. Deprecated requirements shall be marked as inactive, not deleted.

---

## Example Requirement Entry (YAML)

```yaml
- id: SYS-001
  title: Deterministic System Behavior
  description: >
    The system shall produce reproducible outputs when executed
    with identical inputs and configuration parameters.
```

## Traceability Policy
- Each requirement must map to at least one verification artifact.
- Traceability matrices are auto-generated.
- Manual editing of generated traceability files is prohibited.