from pathlib import Path
import xml.etree.ElementTree as ET


def compute_requirement_coverage(matrix):
    """
    Calculate requirement coverage statistics.

    Returns:
        coverage_percent, tested_count, total_count, untested_requirements
    """

    total = len(matrix)

    tested = [
        r for r in matrix
        if r.get("status") in ("PASS", "LINKED")
    ]

    untested = [
        r["requirement_id"]
        for r in matrix
        if r.get("status") == "UNTESTED"
    ]

    tested_count = len(tested)

    coverage = 0.0
    if total > 0:
        coverage = (tested_count / total) * 100

    return coverage, tested_count, total, untested

def compute_code_coverage(project_root):
    """
    Parse coverage.xml to compute overall coverage and
    collect uncovered lines per file.
    """

    coverage_xml = coverage_xml_path(project_root)

    if not coverage_xml.exists():
        return None, {}

    tree = ET.parse(coverage_xml)
    root = tree.getroot()

    coverage_percent = float(root.attrib.get("line-rate", 0)) * 100

    uncovered = {}

    for cls in root.findall(".//class"):

        filename = cls.attrib["filename"]

        missing = []

        for line in cls.findall(".//line"):

            if line.attrib.get("hits") == "0":
                missing.append(int(line.attrib["number"]))

        if missing:
            uncovered[filename] = sorted(missing)

    return coverage_percent, uncovered

def save_uncovered_lines(project_root, uncovered_lines):

    output = project_root / "artifacts" / "coverage" / "uncovered_lines.txt"

    with output.open("w") as f:

        for file, lines in sorted(uncovered_lines.items()):

            f.write(f"{file}\n")

            for ln in lines:
                f.write(f"  line {ln}\n")

            f.write("\n")

    print(f"[Coverage] Uncovered lines saved to {output}")

def coverage_xml_path(project_root: Path):
    return project_root / "artifacts" / "coverage" / "coverage.xml"