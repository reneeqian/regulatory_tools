import yaml
import re
from pathlib import Path

def extract_requirement_marks(test_dir: Path):
    pattern = re.compile(
        r'(?:pytest\.mark\.)?requirement\(["\']([A-Z]+-\d{3})["\']\)'
    )
    found = set()

    for file in test_dir.rglob("test_*.py"):
        text = file.read_text()
        found.update(pattern.findall(text))

    return found


def load_requirements(path: Path):
    data = yaml.safe_load(path.read_text())
    return {req["id"] for req in data["requirements"]}


def validate_traceability(requirements_yaml: Path, test_dir: Path):
    declared = load_requirements(requirements_yaml)
    tested = extract_requirement_marks(test_dir)

    missing = declared - tested
    untracked = tested - declared

    return missing, untracked


REQUIREMENT_PATTERN = re.compile(r'requirement\(["\']([A-Z]+-\d{3})["\']\)')


def find_unmarked_tests(test_dir: Path):
    """
    Returns list of test file paths that contain test functions
    but do not reference any requirement IDs.
    """
    marker_pattern = re.compile(
        r'(?:pytest\.mark\.)?requirement\(["\']([A-Z]+-\d{3})["\']\)'
    )
    test_function_pattern = re.compile(r'def test_')

    unmarked = []

    for test_file in test_dir.rglob("test_*.py"):
        content = test_file.read_text()

        # Detect test functions
        has_test_function = re.search(r"def test_", content)

        # Detect requirement markers
        has_requirement_marker = REQUIREMENT_PATTERN.search(content)

        if has_test_function and not has_requirement_marker:
            unmarked.append(str(test_file))

    return sorted(unmarked)
