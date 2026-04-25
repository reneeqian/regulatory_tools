import re
from pathlib import Path

import yaml

REQ_ID_REGEX = r"(?:[A-Z]+-)?[A-Z]+-\d{3,}"
REQ_ID_PATTERN = re.compile(rf"^{REQ_ID_REGEX}$")
REQ_MARK_PATTERN = re.compile(
    rf'(?:pytest\.mark\.)?requirement\(["\']({REQ_ID_REGEX})["\']\)'
)


def extract_requirement_marks(test_dir: Path) -> set[str]:

    found: set[str] = set()

    for file in test_dir.rglob("test_*.py"):
        text = file.read_text()
        found.update(REQ_MARK_PATTERN.findall(text))

    return found


def load_requirements(path: Path) -> set[str]:

    data = yaml.safe_load(path.read_text())

    if "requirements" not in data:
        raise Exception("Invalid requirements.yaml: missing 'requirements' field")

    ids: set[str] = set()

    for req in data["requirements"]:

        req_id = req.get("id")

        if req_id is None:
            raise Exception("Requirement missing 'id' field")

        if not REQ_ID_PATTERN.match(req_id):
            raise Exception(f"Invalid requirement ID format: {req_id}")

        if req_id in ids:
            raise Exception(f"Duplicate requirement ID detected: {req_id}")

        ids.add(req_id)

    return ids


def validate_traceability(
    requirements_yaml: Path, test_dir: Path
) -> tuple[set[str], set[str]]:

    declared = load_requirements(requirements_yaml)
    tested = extract_requirement_marks(test_dir)

    missing = declared - tested
    untracked = tested - declared

    return missing, untracked


def find_unmarked_tests(test_dir: Path) -> list[str]:

    test_function_pattern = re.compile(r"def test_")

    unmarked: list[str] = []

    for test_file in test_dir.rglob("test_*.py"):

        content = test_file.read_text()

        has_test_function = test_function_pattern.search(content)
        has_requirement_marker = REQ_MARK_PATTERN.search(content)

        if has_test_function and not has_requirement_marker:
            unmarked.append(str(test_file))

    return sorted(unmarked)
