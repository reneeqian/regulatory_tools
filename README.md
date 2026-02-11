# Regulatory Tools

Automation-first infrastructure for generating traceable, reproducible, FDA-ready regulatory artifacts for Software as a Medical Device (SaMD).

---

## Purpose

`regulatory-tools` provides structured automation for:

- Requirement management
- Traceability matrix generation
- Evidence artifact validation
- Regulatory documentation generation
- Artifact provenance tracking
- CI-integrated compliance checks

The goal is to eliminate manual regulatory document assembly and replace it with deterministic, machine-generated outputs.

This repository is designed to support AI systems targeting Class II and Class III FDA submissions.

---

## Design Philosophy

Regulatory documentation should not be manually written from scratch.

It should be:

- Derived from structured data
- Generated deterministically
- Version-controlled
- Machine-validated
- Fully traceable to code and test artifacts
- Reproducible under CI conditions

Regulatory documentation becomes a byproduct of disciplined engineering.

---

## Core Capabilities

### Requirement Management

- Machine-readable YAML requirement definitions
- Unique ID validation
- Lifecycle state support (Draft, Approved, Deprecated)
- Version tracking
- Requirement coverage enforcement

### Traceability Matrix Generation

- Automated linking of:
  - Requirements
  - Unit tests
  - Integration tests
  - Evidence artifacts
  - Training outputs
- Detection of:
  - Unverified requirements
  - Orphan tests
  - Missing references

### Evidence Handling

- Structured evidence report validation
- JSON-serializable evidence artifacts
- Provenance metadata enforcement
- Timestamp and version validation
- Artifact integrity verification support

### Documentation Generation

- Template-driven document generation
- Deterministic output formats
- Machine-readable + human-readable outputs
- Support for:
  - Software Requirements Specification (SRS)
  - Verification Reports
  - Traceability Matrices
  - Design Control Artifacts
  - Submission-ready technical appendices

### CI Integration

- Deterministic pass/fail enforcement
- Automated requirement coverage checks
- Structured summary outputs
- Designed for pipeline execution without manual intervention

---

## Regulatory Alignment

This repository is designed to support alignment with:

- FDA SaMD guidance
- FDA AI/ML lifecycle recommendations
- IEC 62304 software lifecycle processes
- 21 CFR 820 design controls
- Good Machine Learning Practice (GMLP)
- Pre-submission technical documentation preparation

It does not replace regulatory expertise.  
It provides structured automation to support it.

---

## Intended Use

This repository is intended for:

- AI medical device development teams
- Startups preparing FDA submissions
- Engineering organizations implementing design controls
- Consultants building regulated AI infrastructure
- Teams preparing for audit or due diligence

---

## Architecture Role

If `medical-image-ai-toolkit` is the engineering engine,
`regulatory-tools` is the compliance automation layer.

Together they form:

Engineering Evidence → Structured Artifacts → Automated Traceability → Regulatory Documentation

---

## What This Is Not

- Not a Word document generator
- Not a compliance checklist
- Not a substitute for regulatory strategy
- Not a manual documentation framework

It is a deterministic regulatory automation engine.

---

## Maturity Intent

This system is designed to support development processes appropriate for:

- Class II devices
- High-risk Class III AI systems
- Pre-market submission documentation
- Audit-ready development infrastructure
- Investor and technical diligence review

---

## Long-Term Vision

The long-term vision is a fully automated regulatory pipeline where:

- Code commits update requirement coverage
- Training runs generate structured evidence
- CI enforces compliance constraints
- Regulatory documentation is generated automatically
- Traceability is always current

Regulatory quality becomes a property of the system, not a last-minute activity.

---

## License

(Define per project needs.)
