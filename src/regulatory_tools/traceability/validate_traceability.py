import yaml
import re
from pathlib import Path

def extract_requirement_marks(test_dir: Path):
    pattern = re.compile(r'requirement\("([A-Z\-0-9]+)"\)')
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
