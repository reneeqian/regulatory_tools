from pathlib import Path
import json
import pytest
import sys

from regulatory_tools.evidence.evidence_report import EvidenceReport, generate_evidence_summary
from regulatory_tools.traceability import __main__ as traceability_main
from regulatory_tools.traceability.generator import build_trace_matrix
from regulatory_tools.traceability.coverage import (
    compute_code_coverage,
    compute_requirement_coverage,
    coverage_xml_path,
    save_uncovered_lines,
)
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
    """
    Creates a single evidence run directory using
    the CURRENT expected schema:
        {
            "test_id": "...",
            "requirements": ["VER-1"],
            "result": "PASS"
        }
    """
    run_dir = root / "20260101_120000"
    run_dir.mkdir(parents=True)

    record_1 = {
        "test_id": "test_something",
        "requirements": ["VER-001"],
        "result": "PASS",
    }

    record_2 = {
        "test_id": "test_other",
        "requirements": ["VER-002"],
        "result": "PASS",
    }

    (run_dir / "test_something.json").write_text(json.dumps(record_1))
    (run_dir / "test_other.json").write_text(json.dumps(record_2))

    return run_dir


# ----------------------------
# Tests
# ----------------------------
@pytest.mark.requirement("DOC-004")
@pytest.mark.requirement("INF-001")
@pytest.mark.requirement("INF-004")
def test_evidence_summary(tmp_path):

    run = tmp_path / "run"
    run.mkdir()

    record = {
        "test_id": "test_example",
        "requirements": ["VER-001"],
        "result": "PASS",
    }

    (run / "rec.json").write_text(json.dumps(record))

    report = generate_evidence_summary(run)

    assert report["total_tests"] == 1
    

@pytest.mark.requirement("INF-004")
def test_invalid_evidence_schema(tmp_path: Path):

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence"

    evidence_root.mkdir()

    create_dummy_requirements(req_yaml)

    run = evidence_root / "run"
    run.mkdir()

    bad_record = {
        "requirements": ["VER-001"]
    }

    (run / "bad.json").write_text(json.dumps(bad_record))

    matrix = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    assert matrix


@pytest.mark.requirement("INF-001")
def test_latest_evidence_run_used(tmp_path: Path):

    req_yaml = tmp_path / "requirements.yaml"
    evidence_root = tmp_path / "evidence_runs"

    evidence_root.mkdir()

    create_dummy_requirements(req_yaml)

    create_dummy_evidence(evidence_root)

    newer = evidence_root / "20260102_120000"
    newer.mkdir()

    record = {
        "test_id": "test_new",
        "requirements": ["VER-001"],
        "result": "FAIL",
    }

    (newer / "fail.json").write_text(json.dumps(record))

    matrix = build_trace_matrix(
        requirements_yaml=req_yaml,
        evidence_root=evidence_root,
    )

    matrix_by_id = {row["requirement_id"]: row for row in matrix}

    assert matrix_by_id["VER-001"]["status"] == "FAIL"


@pytest.mark.requirement("INF-001")
def test_evidence_report_serializes_and_merges(tmp_path, capsys):

    class Provider:
        def get_ids(self, tag):
            return {
                "tag-a": ["VER-001"],
                "tag-b": ["VER-002"],
            }.get(tag, [])

    report = EvidenceReport(
        subject="Serialization test",
        test_id="tests/test_example.py::test_case",
        requirement_provider=Provider(),
    )
    report.info("informational note", "tag-a", "ctx-a")
    report.warn("warning note", "tag-b")

    child = EvidenceReport(subject="child")
    child.error("child error", "tag-a", "child-ctx")
    report.merge(child, prefix="patient=P1")

    assert report.result == "FAIL"
    assert report.has_errors
    assert "child error" in report.summary()
    assert "[tag-a]" in report.to_string()

    payload = report.to_dict()
    assert payload["requirements"] == ["VER-001", "VER-002"]
    assert payload["requirement_tags"] == ["tag-a", "tag-b"]
    assert payload["issues"][0]["requirement_tag"] == "tag-a"

    markdown = report.to_markdown()
    assert "Serialization test" in markdown
    assert "child error" in markdown

    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    report.save(json_path)
    report.save(md_path)
    report.print_summary()

    assert json.loads(json_path.read_text())["result"] == "FAIL"
    assert "warning note" in md_path.read_text()
    assert "Serialization test" in capsys.readouterr().out


@pytest.mark.requirement("INF-001")
def test_evidence_report_auto_save_and_invalid_format(tmp_path, capsys):

    class EmptyProvider:
        def get_ids(self, tag):
            return []

    report = EvidenceReport(
        subject="Autosave test",
        requirement_provider=EmptyProvider(),
    )
    report.info("missing mapping", "unknown-tag")

    resolved = report.resolve_requirement_ids()
    assert resolved == set()
    assert "No requirement mapping" in capsys.readouterr().out

    report.auto_save("suite::test/name", tmp_path)
    saved = list(tmp_path.glob("*.json"))
    assert len(saved) == 1
    assert "suite_test_name" in saved[0].name

    with pytest.raises(ValueError):
        report.save(tmp_path / "report.txt")


@pytest.mark.requirement("INF-004")
def test_generate_evidence_summary_skips_invalid_json(tmp_path):

    (tmp_path / "pass.json").write_text(json.dumps({"result": "PASS"}))
    (tmp_path / "fail.json").write_text(json.dumps({"result": "FAIL"}))
    (tmp_path / "broken.json").write_text("{")

    summary = generate_evidence_summary(tmp_path)

    assert summary == {
        "total_tests": 2,
        "passed": 1,
        "failed": 1,
    }


@pytest.mark.requirement("VER-005")
def test_compute_code_coverage_and_save_uncovered_lines(tmp_path):

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

    assert percent == 75.0
    assert uncovered == {"pkg/module.py": [11, 12]}
    assert coverage_xml_path(tmp_path) == coverage_xml
    assert "line 11" in (coverage_dir / "uncovered_lines.txt").read_text()


@pytest.mark.requirement("VER-005")
def test_compute_requirement_coverage_and_find_unmarked_tests(tmp_path):

    matrix = [
        {"requirement_id": "VER-001", "status": "PASS"},
        {"requirement_id": "VER-002", "status": "LINKED"},
        {"requirement_id": "VER-003", "status": "UNTESTED"},
    ]

    coverage, tested, total, untested = compute_requirement_coverage(matrix)

    assert coverage == pytest.approx(66.66666666666666)
    assert tested == 2
    assert total == 3
    assert untested == ["VER-003"]

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_marked.py").write_text(
        'import pytest\n\n@pytest.mark.requirement("VER-001")\ndef test_marked():\n    assert True\n'
    )
    (test_dir / "test_unmarked.py").write_text(
        "def test_unmarked():\n    assert True\n"
    )

    assert find_unmarked_tests(test_dir) == [str(test_dir / "test_unmarked.py")]


@pytest.mark.requirement("SYS-001")
def test_traceability_module_main_dispatches(monkeypatch, tmp_path):

    called = {}

    def fake_generate(project_root):
        called["project_root"] = project_root

    monkeypatch.setattr(traceability_main, "generate_traceability_matrix", fake_generate)
    monkeypatch.setattr(sys, "argv", ["traceability", str(tmp_path)])

    traceability_main.main()

    assert called["project_root"] == tmp_path


@pytest.mark.requirement("SYS-001")
def test_traceability_module_main_requires_project_root(monkeypatch, capsys):

    monkeypatch.setattr(sys, "argv", ["traceability"])

    with pytest.raises(SystemExit) as exc:
        traceability_main.main()

    assert exc.value.code == 1
    assert "Usage:" in capsys.readouterr().out
