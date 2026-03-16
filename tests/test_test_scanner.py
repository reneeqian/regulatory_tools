from pathlib import Path
from regulatory_tools.traceability.test_scanner import collect_requirement_markers


def test_scan_tests_detects_tests(tmp_path):

    test_dir = tmp_path / "tests"
    test_dir.mkdir()

    f = test_dir / "test_example.py"
    f.write_text(
    '''
import pytest

@pytest.mark.requirement("REQ-001")
def test_a():
    assert True
'''
    )

    tests = collect_requirement_markers(test_dir)

    assert "REQ-001" in tests
    assert len(tests["REQ-001"]) == 1