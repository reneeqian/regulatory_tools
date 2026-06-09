import json
import sys
from pathlib import Path

import pytest

from regulatory_tools.evidence.evidence_report import EvidenceReport, generate_evidence_summary
from regulatory_tools.traceability import __main__ as traceability_main
from regulatory_tools.traceability.coverage import (
    compute_code_coverage,
    compute_requirement_coverage,
    coverage_xml_path,
    save_uncovered_lines,
)
from regulatory_tools.traceability.generator import build_trace_matrix
from regulatory_tools.traceability.validate_traceability import find_unmarked_tests

# ----------------------------
# Helpers
# ----------------------------


def create_dummy_requirements(path: Path):
    path.write_text(
        """
requirements:
  - id: VER-001
    description: Dummy requirement 1
  - id: VER-002
    description: Dummy requirement 2
  - id: VER-003
    description: Dummy requirement 3
"""
    )


def create_dummy_evidence(root: Path):
    run_dir = root / "20260101_120000"
    run_dir.mkdir(parents=True)
    record_1 = {"test_id": "test_something", "requirements": ["VER-001"], "result": "PASS"}
    record_2 = {"test_id": "test_other", "requirements": ["VER-002"], "result": "PASS"}
    (run_dir / "test_something.json").write_text(json.dumps(record_1))
    (run_dir / "test_other.json").write_text(json.dumps(record_2))
    return run_dir


# ----------------------------
# Tests
# ----------------------------


@pytest.mark.requirement("DOC-004")
@pytest.mark.requirement("INF-001")
@pytest.mark.requirement("INF-004")
def test_evidence_summary(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="generate_evidence_summary aggregates evidence artifacts and reports total_tests count"
    )

    run = tmp_path / "run"
    run.mkdir()
    record = {"test_id": "test_example", "requirements": ["VER-001"], "result": "PASS"}
    (run / "rec.json").write_text(json.dumps(record))

    result = generate_evidence_summary(run)

    report.info(f"total_tests={result['total_tests']}", "INF-001")
    report.info("evidence_artifact_associated_with_requirement", "INF-004")
    report.info("summary_generated_from_artifacts", "DOC-004")
    report.auto_save("doc004_inf001_inf004_evidence_summary", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert result["total_tests"] == 1


@pytest.mark.requirement("INF-004")
def test_invalid_evidence_schema(tmp_path: Path, evidence_output_dir):
    report = EvidenceReport(
        subject="build_trace_matrix skips evidence files missing required 'test_id' field without crashing"
    )

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    create_dummy_requirements(req_yaml)
    run = evidence_root / "run"
    run.mkdir()
    bad_record = {"requirements": ["VER-001"]}  # missing test_id
    (run / "bad.json").write_text(json.dumps(bad_record))

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)

    report.info(f"matrix_built_without_crash={bool(matrix)}", "INF-004")
    report.auto_save("inf004_invalid_evidence_schema", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert matrix


@pytest.mark.requirement("INF-001")
def test_latest_evidence_run_used(tmp_path: Path, evidence_output_dir):
    report = EvidenceReport(
        subject="build_trace_matrix uses the most recent evidence run when multiple runs exist"
    )

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence_runs"
    evidence_root.mkdir()
    create_dummy_requirements(req_yaml)
    create_dummy_evidence(evidence_root)

    newer = evidence_root / "20260102_120000"
    newer.mkdir()
    record = {"test_id": "test_new", "requirements": ["VER-001"], "result": "FAIL"}
    (newer / "fail.json").write_text(json.dumps(record))

    matrix = build_trace_matrix(requirements_yaml=req_yaml, evidence_root=evidence_root)
    matrix_by_id = {row["requirement_id"]: row for row in matrix}

    report.info(f"VER-001_status_from_latest_run={matrix_by_id['VER-001']['status']}", "INF-001")
    report.auto_save("inf001_latest_evidence_run_used", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert matrix_by_id["VER-001"]["status"] == "FAIL"


@pytest.mark.requirement("INF-001")
def test_evidence_report_serializes_and_merges(tmp_path, capsys, evidence_output_dir):
    report = EvidenceReport(
        subject="EvidenceReport serializes to dict/json/markdown and merges child reports correctly"
    )

    class Provider:
        def get_ids(self, tag):
            return {"tag-a": ["VER-001"], "tag-b": ["VER-002"]}.get(tag, [])

    inner = EvidenceReport(
        subject="Serialization test",
        test_id="tests/test_example.py::test_case",
        requirement_provider=Provider(),
    )
    inner.info("informational note", "tag-a", "ctx-a")
    inner.warn("warning note", "tag-b")

    child = EvidenceReport(subject="child")
    child.error("child error", "tag-a", "child-ctx")
    inner.merge(child, prefix="patient=P1")

    assert inner.result == "FAIL"
    assert inner.has_errors
    assert "child error" in inner.summary()
    assert "[tag-a]" in inner.to_string()

    payload = inner.to_dict()
    assert payload["requirements"] == ["VER-001", "VER-002"]
    assert payload["requirement_tags"] == ["tag-a", "tag-b"]
    assert payload["issues"][0]["requirement_tag"] == "tag-a"

    markdown = inner.to_markdown()
    assert "Serialization test" in markdown
    assert "child error" in markdown

    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    inner.save(json_path)
    inner.save(md_path)
    inner.print_summary()

    assert json.loads(json_path.read_text())["result"] == "FAIL"
    assert "warning note" in md_path.read_text()
    assert "Serialization test" in capsys.readouterr().out

    report.info("serialization_round_trip_correct=True, merge_propagates_errors=True", "INF-001")
    report.auto_save("inf001_evidence_report_serializes_and_merges", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("INF-001")
def test_evidence_report_auto_save_and_invalid_format(tmp_path, capsys, evidence_output_dir):
    report = EvidenceReport(
        subject="EvidenceReport.auto_save sanitizes filenames and raises on unsupported formats"
    )

    class EmptyProvider:
        def get_ids(self, tag):
            return []

    inner = EvidenceReport(subject="Autosave test", requirement_provider=EmptyProvider())
    inner.info("missing mapping", "unknown-tag")

    resolved = inner.resolve_requirement_ids()
    assert resolved == set()
    assert "No requirement mapping" in capsys.readouterr().out

    inner.auto_save("suite::test/name", tmp_path)
    saved = list(tmp_path.glob("*.json"))
    assert len(saved) == 1
    assert "suite_test_name" in saved[0].name

    raised = False
    try:
        inner.save(tmp_path / "report.txt")
    except ValueError:
        raised = True
    assert raised

    report.info(f"filename_sanitized=True, unsupported_format_raises={raised}", "INF-001")
    report.auto_save("inf001_evidence_report_auto_save_and_invalid_format", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("INF-004")
def test_generate_evidence_summary_skips_invalid_json(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="generate_evidence_summary skips malformed JSON files without crashing"
    )

    (tmp_path / "pass.json").write_text(json.dumps({"result": "PASS"}))
    (tmp_path / "fail.json").write_text(json.dumps({"result": "FAIL"}))
    (tmp_path / "broken.json").write_text("{")

    summary = generate_evidence_summary(tmp_path)

    report.info(
        f"total={summary['total_tests']}, passed={summary['passed']}, failed={summary['failed']}",
        "INF-004",
    )
    report.auto_save("inf004_generate_evidence_summary_skips_invalid_json", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert summary == {"total_tests": 2, "passed": 1, "failed": 1}


@pytest.mark.requirement("VER-005")
def test_compute_code_coverage_and_save_uncovered_lines(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="compute_code_coverage parses coverage.xml and save_uncovered_lines writes line numbers"
    )

    coverage_dir = tmp_path / "artifacts" / "coverage"
    coverage_dir.mkdir(parents=True)
    coverage_xml = coverage_dir / "coverage.xml"
    coverage_xml.write_text(
        """<?xml version="1.0" ?>
<coverage line-rate="0.75">
  <packages>
    <package>
      <classes>
        <class filename="pkg/module.py">
          <lines>
            <line number="10" hits="1"/>
            <line number="11" hits="0"/>
            <line number="12" hits="0"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
    )

    percent, uncovered = compute_code_coverage(tmp_path)
    save_uncovered_lines(tmp_path, uncovered)

    report.info(f"coverage={percent}%, uncovered_lines={uncovered}", "VER-005")
    report.auto_save("ver005_compute_code_coverage_and_save_uncovered_lines", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert percent == 75.0
    assert uncovered == {"pkg/module.py": [11, 12]}
    assert coverage_xml_path(tmp_path) == coverage_xml
    assert "line 11" in (coverage_dir / "uncovered_lines.txt").read_text()


@pytest.mark.requirement("VER-005")
def test_compute_requirement_coverage_and_find_unmarked_tests(tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="compute_requirement_coverage counts PASS+LINKED as tested; find_unmarked_tests detects unannotated test functions"
    )

    matrix = [
        {"requirement_id": "VER-001", "status": "PASS"},
        {"requirement_id": "VER-002", "status": "LINKED"},
        {"requirement_id": "VER-003", "status": "UNTESTED"},
    ]

    coverage, tested, total, untested = compute_requirement_coverage(matrix)

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_marked.py").write_text(
        'import pytest\n\n@pytest.mark.requirement("VER-001")\ndef test_marked():\n    assert True\n'
    )
    (test_dir / "test_unmarked.py").write_text("def test_unmarked():\n    assert True\n")

    unmarked = find_unmarked_tests(test_dir)

    report.info(
        f"coverage={coverage}%, tested={tested}, total={total}, untested={untested}", "VER-005"
    )
    report.info(
        f"unmarked_test_detected={str(test_dir / 'test_unmarked.py') in unmarked}", "VER-005"
    )
    report.auto_save(
        "ver005_compute_requirement_coverage_and_find_unmarked_tests", evidence_output_dir
    )
    assert not report.has_errors, report.summary()
    assert coverage == pytest.approx(66.66666666666666)
    assert tested == 2
    assert total == 3
    assert untested == ["VER-003"]
    assert find_unmarked_tests(test_dir) == [str(test_dir / "test_unmarked.py")]


@pytest.mark.requirement("SYS-001")
def test_traceability_module_main_dispatches(monkeypatch, tmp_path, evidence_output_dir):
    report = EvidenceReport(
        subject="regulatory_tools.traceability.__main__.main dispatches to generate_traceability_matrix with the project root argument"
    )

    called = {}

    def fake_generate(project_root):
        called["project_root"] = project_root

    monkeypatch.setattr(traceability_main, "generate_traceability_matrix", fake_generate)
    monkeypatch.setattr(sys, "argv", ["traceability", str(tmp_path)])

    traceability_main.main()

    report.info(f"dispatched_with_correct_root={called['project_root'] == tmp_path}", "SYS-001")
    report.auto_save("sys001_traceability_module_main_dispatches", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert called["project_root"] == tmp_path


@pytest.mark.requirement("SYS-001")
def test_traceability_module_main_requires_project_root(monkeypatch, capsys, evidence_output_dir):
    report = EvidenceReport(
        subject="regulatory_tools.traceability.__main__.main exits 1 with usage message when project root argument is missing"
    )

    monkeypatch.setattr(sys, "argv", ["traceability"])

    with pytest.raises(SystemExit) as exc:
        traceability_main.main()

    out = capsys.readouterr().out
    report.info(f"exit_code={exc.value.code}, usage_printed={'Usage:' in out}", "SYS-001")
    report.auto_save("sys001_traceability_module_main_requires_project_root", evidence_output_dir)
    assert not report.has_errors, report.summary()
    assert exc.value.code == 1
    assert "Usage:" in out
