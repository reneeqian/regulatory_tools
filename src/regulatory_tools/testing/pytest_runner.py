import subprocess
from pathlib import Path
import sys


def run_pytest_with_coverage(project_root: Path, source_dir: Path):
    test_dir = project_root / "tests"
    coverage_dir = project_root / "artifacts" / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "pytest",
            str(test_dir),
            f"--cov={source_dir}",
            "--cov-report=term",
            f"--cov-report=html:{coverage_dir / 'html'}",
            f"--cov-report=xml:{coverage_dir / 'coverage.xml'}",
            "--cov-fail-under=85",
        ],
        cwd=project_root,
    )

    if result.returncode != 0:
        print("Pytest failed.")
        sys.exit(1)