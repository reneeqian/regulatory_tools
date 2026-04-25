import shutil
import subprocess
import sys
from pathlib import Path


def detect_source_package(project_root):

    src = project_root / "src"

    packages = [
        p for p in src.iterdir()
        if p.is_dir() and (p / "__init__.py").exists()
    ]

    if not packages:
        raise RuntimeError("No package found in src/")

    return packages[0]

def run_pytest_with_coverage(project_root: Path):
    test_dir = project_root / "tests"
    coverage_dir = project_root / "artifacts" / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    source = detect_source_package(project_root)

    # Skip pytest if no tests exist
    if not any(test_dir.rglob("test_*.py")):
        print("No tests detected — skipping pytest execution.")
        return

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_dir),
            f"--cov={source}",
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

    # Copy coverage.xml to the project root so forge can locate it with skip_test_run=True.
    # Forge expects coverage.xml at the project root by default.
    xml_in_artifacts = coverage_dir / "coverage.xml"
    if xml_in_artifacts.exists():
        shutil.copy(xml_in_artifacts, project_root / "coverage.xml")
