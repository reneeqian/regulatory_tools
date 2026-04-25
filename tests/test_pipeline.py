from pathlib import Path
from regulatory_tools.traceability.pipeline import generate_traceability_matrix
from regulatory_tools.traceability.test_scanner import collect_requirement_markers
from regulatory_tools.traceability.generator import build_trace_matrix, apply_test_markers
from regulatory_tools.traceability.coverage import compute_requirement_coverage
from regulatory_tools.testing.pytest_runner import run_pytest_with_coverage

import pytest
import sys

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

# ----------------------------
# Tests
# ----------------------------

@pytest.mark.requirement("VER-005")
@pytest.mark.requirement("DOC-003")
@pytest.mark.requirement("SYS-002")
def test_pipeline_execution(tmp_path):

    project = tmp_path / "proj"

    (project / "docs").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "artifacts" / "evidence_runs").mkdir(parents=True)

    (project / "docs" / "requirements.yaml").write_text(
        """
requirements:
  - id: VER-001
    description: example
"""
    )

    generate_traceability_matrix(project)

    output = project / "docs" / "traceability_matrix.md"

    assert output.exists()
    
@pytest.mark.requirement("SYS-001")
@pytest.mark.requirement("SYS-002")
def test_traceability_cli_execution(tmp_path):

    project = tmp_path / "proj"

    (project / "docs").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "artifacts" / "evidence_runs").mkdir(parents=True)

    (project / "docs" / "requirements.yaml").write_text(
        """
requirements:
  - id: VER-001
    description: example
"""
    )

    generate_traceability_matrix(project)

    assert (project / "docs" / "traceability_matrix.md").exists()
    

@pytest.mark.requirement("INF-004")
def test_scan_tests_detects_tests(tmp_path):

    test_dir = tmp_path / "tests"
    test_dir.mkdir()

    f = test_dir / "test_example.py"
    f.write_text(
    '''
import pytest

@pytest.mark.requirement("VER-001")
def test_a():
    assert True
'''
    )

    tests = collect_requirement_markers(test_dir)

    assert "VER-001" in tests
    assert len(tests["VER-001"]) == 1
    
    
@pytest.mark.requirement("SYS-001")
def test_run_tests_and_trace_smoke(tmp_path):
    """
    Ensures CLI pipeline executes.
    """

    from regulatory_tools.testing import run_tests_and_trace

    project = tmp_path / "proj"
    project.mkdir()

    (project / "tests").mkdir()
    (project / "docs").mkdir()

    src = project / "src"
    src.mkdir()

    pkg = src / "dummy_pkg"
    pkg.mkdir()

    (pkg / "__init__.py").write_text("")

    create_dummy_requirements(project / "docs" / "requirements.yaml")

    run_tests_and_trace(project, min_grade=None)


@pytest.mark.requirement("VER-002")
@pytest.mark.requirement("VER-005")
def test_requirement_markers_count_as_linked_coverage(tmp_path):

    project = tmp_path / "proj"
    (project / "docs").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "artifacts" / "evidence_runs").mkdir(parents=True)

    (project / "docs" / "requirements.yaml").write_text(
        """
requirements:
  - id: VER-001
    description: example
  - id: VER-002
    description: second example
"""
    )

    (project / "tests" / "test_example.py").write_text(
        '''
import pytest

@pytest.mark.requirement("VER-001")
def test_a():
    assert True
'''
    )

    matrix = build_trace_matrix(
        requirements_yaml=project / "docs" / "requirements.yaml",
        evidence_root=project / "artifacts" / "evidence_runs",
    )
    marker_links = collect_requirement_markers(project / "tests", project)
    apply_test_markers(matrix, marker_links)

    matrix_by_id = {row["requirement_id"]: row for row in matrix}

    assert matrix_by_id["VER-001"]["status"] == "LINKED"
    assert "tests/test_example.py::test_a" in matrix_by_id["VER-001"]["tests"]
    assert matrix_by_id["VER-002"]["status"] == "UNTESTED"

    coverage, tested, total, untested = compute_requirement_coverage(matrix)

    assert coverage == 50.0
    assert tested == 1
    assert total == 2
    assert untested == ["VER-002"]


@pytest.mark.requirement("SYS-001")
def test_run_pytest_with_coverage_uses_active_python(tmp_path, monkeypatch):

    project = tmp_path / "proj"
    test_dir = project / "tests"
    pkg_dir = project / "src" / "dummy_pkg"

    test_dir.mkdir(parents=True)
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("")
    (test_dir / "test_example.py").write_text("def test_ok():\n    assert True\n")

    captured = {}

    class DummyResult:
        returncode = 0

    def fake_run(args, cwd):
        captured["args"] = args
        captured["cwd"] = cwd
        return DummyResult()

    monkeypatch.setattr("subprocess.run", fake_run)

    run_pytest_with_coverage(project)

    assert captured["args"][:3] == [sys.executable, "-m", "pytest"]
    assert captured["cwd"] == project
