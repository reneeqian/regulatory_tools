<!-- AUTO-GENERATED FILE. DO NOT EDIT MANUALLY. -->

# Requirements Traceability Matrix

## Requirement Coverage

**Coverage:** 100.0% (19 / 19 requirements tested)

## Code Coverage

**Line Coverage:** 86.8%

Detailed uncovered lines saved in `artifacts/coverage/uncovered_lines.txt`

| Requirement ID | Title | Linked Tests | Evidence Artifacts | Status |
|----------------|-------------|--------------|--------------------|--------|
| DOC-001 | Machine-Readable Requirements Definition | tests/test_project_structure.py::test_project_documentation_structure |  | LINKED |
| DOC-002 | Basic Project Documentation | tests/test_project_structure.py::test_project_documentation_structure |  | LINKED |
| DOC-003 | Traceability Documentation Generation | tests/test_pipeline.py::test_pipeline_execution, tests/test_traceability_workflow.py::test_full_traceability_workflow |  | LINKED |
| DOC-004 | Requirements Summary Generation | tests/test_evidence.py::test_evidence_summary, tests/test_traceability_workflow.py::test_evidence_summary_generation |  | LINKED |
| INF-001 | Artifact Collection Support | tests/test_evidence.py::test_evidence_report_auto_save_and_invalid_format, tests/test_evidence.py::test_evidence_report_serializes_and_merges, tests/test_evidence.py::test_evidence_summary, tests/test_evidence.py::test_latest_evidence_run_used |  | LINKED |
| INF-002 | Configuration Schema Validation | tests/test_traceability_workflow.py::test_invalid_yaml_rejected |  | LINKED |
| INF-003 | Verification Artifact Persistence | tests/test_traceability_workflow.py::test_code_coverage_computation, tests/test_traceability_workflow.py::test_full_traceability_workflow |  | LINKED |
| INF-004 | Evidence Artifact Association | tests/test_evidence.py::test_evidence_summary, tests/test_evidence.py::test_generate_evidence_summary_skips_invalid_json, tests/test_evidence.py::test_invalid_evidence_schema, tests/test_pipeline.py::test_scan_tests_detects_tests |  | LINKED |
| RSK-001 | Evidence Classification Support | tests/test_traceability_workflow.py::test_evidence_summary_generation |  | LINKED |
| RSK-002 | Risk Metadata Preservation | tests/test_traceability_workflow.py::test_evidence_summary_generation |  | LINKED |
| SYS-001 | CI-Compatible Execution | tests/test_evidence.py::test_traceability_module_main_dispatches, tests/test_evidence.py::test_traceability_module_main_requires_project_root, tests/test_pipeline.py::test_run_pytest_with_coverage_uses_active_python, tests/test_pipeline.py::test_run_tests_and_trace_smoke, tests/test_pipeline.py::test_traceability_cli_execution, tests/test_traceability_workflow.py::test_traceability_cli_execution |  | LINKED |
| SYS-002 | Deterministic Artifact Generation | tests/test_pipeline.py::test_pipeline_execution, tests/test_pipeline.py::test_traceability_cli_execution, tests/test_traceability_workflow.py::test_code_coverage_computation, tests/test_traceability_workflow.py::test_traceability_matrix_determinism |  | LINKED |
| VER-001 | Requirement Definition Validation | tests/test_traceability_workflow.py::test_duplicate_requirement_ids_detected, tests/test_traceability_workflow.py::test_requirement_validation |  | LINKED |
| VER-002 | Test Reference Validation | tests/test_pipeline.py::test_requirement_markers_count_as_linked_coverage, tests/test_traceability_workflow.py::test_evidence_issue_requirement_ids_link_matrix_when_top_level_missing, tests/test_traceability_workflow.py::test_full_traceability_workflow, tests/test_traceability_workflow.py::test_unknown_requirement_in_evidence |  | LINKED |
| VER-003 | Orphan Requirement Detection | tests/test_traceability_workflow.py::test_empty_evidence_directory, tests/test_traceability_workflow.py::test_full_traceability_workflow |  | LINKED |
| VER-004 | Deterministic Traceability Output | tests/test_traceability_workflow.py::test_traceability_matrix_determinism |  | LINKED |
| VER-005 | Traceability Matrix Generation | tests/test_evidence.py::test_compute_code_coverage_and_save_uncovered_lines, tests/test_evidence.py::test_compute_requirement_coverage_and_find_unmarked_tests, tests/test_pipeline.py::test_pipeline_execution, tests/test_pipeline.py::test_requirement_markers_count_as_linked_coverage, tests/test_traceability_workflow.py::test_full_traceability_workflow |  | LINKED |
| VER-006 | Requirement Reference Validation | tests/test_traceability_workflow.py::test_invalid_requirement_id_format |  | LINKED |
| VER-007 | Deterministic Requirement Parsing | tests/test_traceability_workflow.py::test_requirement_validation |  | LINKED |


---


---
Total Requirements: 19

Tested: 19

Failures: 0
