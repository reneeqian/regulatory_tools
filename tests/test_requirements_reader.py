"""
Tests for regulatory_tools.dhf.requirements_reader (DHF-001, DHF-007).

These tests must fail before RequirementsReader exists (Gate 2 — TDD).
"""
import textwrap
from pathlib import Path

import pytest
import yaml

from regulatory_tools.evidence.evidence_report import EvidenceReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "requirements.yaml"
    p.write_text(textwrap.dedent(content))
    return p


MINIMAL_YAML = """
    metadata:
      project: test_project
      version: 1.0
    requirements:
      - id: SYS-001
        title: System does something
        description: The system shall do something.
      - id: UN-001
        type: user_need
        title: User needs something
        description: A user needs something.
      - id: DSN-001
        type: design_requirement
        title: Design detail
        description: The design shall specify something.
        derived_from: [SYS-001]
      - id: RSK-001
        type: risk_control
        title: Halt on error
        description: The system shall halt on error.
        derived_from: [SYS-001]
"""


# ---------------------------------------------------------------------------
# Import (fails until module exists)
# ---------------------------------------------------------------------------

from regulatory_tools.dhf.requirements_reader import Requirement, RequirementsReader


# ---------------------------------------------------------------------------
# Requirement dataclass
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-001")
def test_requirement_dataclass_has_expected_fields(evidence_output_dir):
    report = EvidenceReport(subject="DHF-001: Requirement dataclass exposes id, type, title, description, tags, derived_from")

    req = Requirement(
        id="SYS-001",
        type="system_requirement",
        title="System does something",
        description="The system shall do something.",
        tags=[],
        derived_from=[],
    )

    assert req.id == "SYS-001"
    assert req.type == "system_requirement"
    assert req.title == "System does something"
    assert req.derived_from == []

    report.info("Requirement dataclass fields present and accessible", "DHF-001")
    report.auto_save("dhf001_requirement_dataclass_fields", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Load — type defaults
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-001")
def test_missing_type_defaults_to_system_requirement(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-001: Entry without `type` defaults to system_requirement")

    path = _write_yaml(tmp_path, MINIMAL_YAML)
    reqs = RequirementsReader.load(path)

    sys_req = next(r for r in reqs if r.id == "SYS-001")
    assert sys_req.type == "system_requirement", f"Expected system_requirement, got {sys_req.type!r}"

    report.info(f"SYS-001 without explicit type → type={sys_req.type!r}", "DHF-001")
    report.auto_save("dhf001_missing_type_defaults", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-001")
def test_explicit_type_values_are_preserved(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-001: Explicit type values user_need, design_requirement, risk_control preserved")

    path = _write_yaml(tmp_path, MINIMAL_YAML)
    reqs = RequirementsReader.load(path)
    by_id = {r.id: r for r in reqs}

    assert by_id["UN-001"].type == "user_need"
    assert by_id["DSN-001"].type == "design_requirement"
    assert by_id["RSK-001"].type == "risk_control"

    report.info("user_need, design_requirement, risk_control all parsed correctly", "DHF-001")
    report.auto_save("dhf001_explicit_type_values", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-001")
def test_missing_derived_from_defaults_to_empty_list(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-001: Entry without derived_from defaults to []")

    path = _write_yaml(tmp_path, MINIMAL_YAML)
    reqs = RequirementsReader.load(path)

    sys_req = next(r for r in reqs if r.id == "SYS-001")
    assert sys_req.derived_from == [], f"Expected [], got {sys_req.derived_from!r}"

    report.info("SYS-001 without derived_from → derived_from=[]", "DHF-001")
    report.auto_save("dhf001_missing_derived_from_defaults", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-001")
def test_derived_from_list_is_parsed(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-001: derived_from list is parsed into list[str]")

    path = _write_yaml(tmp_path, MINIMAL_YAML)
    reqs = RequirementsReader.load(path)
    by_id = {r.id: r for r in reqs}

    assert by_id["DSN-001"].derived_from == ["SYS-001"]
    assert by_id["RSK-001"].derived_from == ["SYS-001"]

    report.info("derived_from=['SYS-001'] parsed correctly for DSN-001 and RSK-001", "DHF-001")
    report.auto_save("dhf001_derived_from_parsed", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# by_type()
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-001")
def test_by_type_returns_only_matching_requirements(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-001: by_type() returns only requirements of the requested type")

    path = _write_yaml(tmp_path, MINIMAL_YAML)
    reader = RequirementsReader(path)

    user_needs = reader.by_type("user_need")
    risk_controls = reader.by_type("risk_control")
    system_reqs = reader.by_type("system_requirement")

    assert len(user_needs) == 1 and user_needs[0].id == "UN-001"
    assert len(risk_controls) == 1 and risk_controls[0].id == "RSK-001"
    assert len(system_reqs) == 1 and system_reqs[0].id == "SYS-001"

    report.info(
        f"by_type: user_need={[r.id for r in user_needs]}, "
        f"risk_control={[r.id for r in risk_controls]}, "
        f"system_requirement={[r.id for r in system_reqs]}",
        "DHF-001",
    )
    report.auto_save("dhf001_by_type_filtering", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-001")
def test_by_type_unknown_type_returns_empty(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-001: by_type() with unknown type string returns empty list")

    path = _write_yaml(tmp_path, MINIMAL_YAML)
    reader = RequirementsReader(path)

    result = reader.by_type("nonexistent_type")
    assert result == []

    report.info("by_type('nonexistent_type') returned []", "DHF-001")
    report.auto_save("dhf001_by_type_unknown", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# derived_from_id() — walk the graph upward
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-007")
def test_derived_from_id_returns_child_requirements(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-007: derived_from_id() returns requirements that list the given ID in derived_from")

    path = _write_yaml(tmp_path, MINIMAL_YAML)
    reader = RequirementsReader(path)

    children = reader.derived_from_id("SYS-001")
    child_ids = {r.id for r in children}

    assert "DSN-001" in child_ids
    assert "RSK-001" in child_ids
    assert "SYS-001" not in child_ids

    report.info(f"derived_from_id('SYS-001') returned {sorted(child_ids)}", "DHF-007")
    report.auto_save("dhf007_derived_from_id_children", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-007")
def test_derived_from_id_with_no_children_returns_empty(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-007: derived_from_id() returns [] when no requirements derive from the given ID")

    path = _write_yaml(tmp_path, MINIMAL_YAML)
    reader = RequirementsReader(path)

    children = reader.derived_from_id("UN-001")
    assert children == []

    report.info("derived_from_id('UN-001') returned [] — no requirements derive from it", "DHF-007")
    report.auto_save("dhf007_derived_from_id_empty", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Backward compatibility — existing requirements.yaml files must still parse
# ---------------------------------------------------------------------------

@pytest.mark.requirement("DHF-001")
def test_existing_requirements_yaml_parses_without_error(evidence_output_dir):
    report = EvidenceReport(subject="DHF-001: RequirementsReader.load() succeeds on regulatory_tools/docs/requirements.yaml")

    reqs_path = Path(__file__).resolve().parents[1] / "docs" / "requirements.yaml"
    reqs = RequirementsReader.load(reqs_path)

    assert len(reqs) > 0
    # All existing entries have no explicit type — they should all default to system_requirement
    for r in reqs:
        assert r.type in {"system_requirement", "user_need", "design_requirement", "risk_control"}, \
            f"{r.id}: unexpected type {r.type!r}"

    report.info(
        f"Loaded {len(reqs)} requirements from regulatory_tools/docs/requirements.yaml — all types valid",
        "DHF-001",
    )
    report.auto_save("dhf001_existing_yaml_backward_compat", evidence_output_dir)
    assert not report.has_errors, report.summary()


# ---------------------------------------------------------------------------
# Multi-file loading and source_file field (DHF-012)
# ---------------------------------------------------------------------------

SRS_YAML = textwrap.dedent("""\
    metadata:
      project: test
      file_role: system_requirements
      allowed_prefixes: [SYS]
      allowed_types: [system_requirement]
      regulatory_role: IEC 62304 §5.2 SRS
    requirements:
      - id: SYS-001
        title: System req
        description: The system shall do something.
""")

DESIGN_YAML = textwrap.dedent("""\
    metadata:
      project: test
      file_role: design_requirements
      allowed_prefixes: [SYS]
      allowed_types: [design_requirement]
      regulatory_role: IEC 62304 §5.4 SDS
    requirements:
      - id: SYS-099
        type: design_requirement
        title: Design detail
        description: The design shall specify something.
        derived_from: [SYS-001]
""")


def _write_split_files(tmp_path: Path) -> tuple[Path, Path]:
    srs = tmp_path / "requirements.yaml"
    srs.write_text(SRS_YAML)
    design = tmp_path / "design.yaml"
    design.write_text(DESIGN_YAML)
    return srs, design


@pytest.mark.requirement("DHF-012")
def test_multi_file_load_merges_requirements(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-012: RequirementsReader([paths]) merges requirements from multiple files into one namespace")

    srs, design = _write_split_files(tmp_path)
    reader = RequirementsReader([srs, design])
    all_ids = {r.id for r in reader.all()}

    assert "SYS-001" in all_ids
    assert "SYS-099" in all_ids
    assert len(reader.all()) == 2

    report.info(f"Merged {len(reader.all())} requirements from 2 files: {sorted(all_ids)}", "DHF-012")
    report.auto_save("dhf012_multi_file_merge", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-012")
def test_source_file_field_is_set_to_path_stem(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-012: Each Requirement.source_file equals the filename stem of its origin file")

    srs, design = _write_split_files(tmp_path)
    reader = RequirementsReader([srs, design])
    by_id = {r.id: r for r in reader.all()}

    assert by_id["SYS-001"].source_file == "requirements", \
        f"Expected 'requirements', got {by_id['SYS-001'].source_file!r}"
    assert by_id["SYS-099"].source_file == "design", \
        f"Expected 'design', got {by_id['SYS-099'].source_file!r}"

    report.info(
        f"SYS-001.source_file={by_id['SYS-001'].source_file!r}, "
        f"SYS-099.source_file={by_id['SYS-099'].source_file!r}",
        "DHF-012",
    )
    report.auto_save("dhf012_source_file_stem", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-012")
def test_single_path_wrapped_in_list_still_works(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-012: RequirementsReader([single_path]) works identically to legacy single-path usage")

    srs, _ = _write_split_files(tmp_path)
    reader = RequirementsReader([srs])
    assert len(reader.all()) == 1
    assert reader.all()[0].id == "SYS-001"
    assert reader.all()[0].source_file == "requirements"

    report.info("Single path in list loads correctly with source_file set", "DHF-012")
    report.auto_save("dhf012_single_path_compat", evidence_output_dir)
    assert not report.has_errors, report.summary()


@pytest.mark.requirement("DHF-012")
def test_duplicate_id_across_files_raises(tmp_path, evidence_output_dir):
    report = EvidenceReport(subject="DHF-012: RequirementsReader raises ValueError when duplicate IDs appear across files")

    srs = tmp_path / "requirements.yaml"
    srs.write_text(SRS_YAML)
    dup = tmp_path / "other.yaml"
    dup.write_text(textwrap.dedent("""\
        metadata:
          project: test
          file_role: other
          allowed_prefixes: [SYS]
          allowed_types: [system_requirement]
        requirements:
          - id: SYS-001
            title: Duplicate
            description: Duplicate ID from another file.
    """))

    with pytest.raises(ValueError, match="SYS-001"):
        RequirementsReader([srs, dup])

    report.info("Duplicate SYS-001 across two files raised ValueError", "DHF-012")
    report.auto_save("dhf012_duplicate_id_across_files", evidence_output_dir)
    assert not report.has_errors, report.summary()
