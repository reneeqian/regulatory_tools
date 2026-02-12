from datetime import datetime
from pathlib import Path
import pytest


# ---------------------------------------------------------------------
# Project Root
# ---------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_root() -> Path:
    """
    Returns the root of the Coronary_prj project.
    """
    return Path(__file__).resolve().parents[1] 

# ---------------------------------------------------------------------
# Evidence Output Directory
# ---------------------------------------------------------------------
@pytest.fixture(scope="session")
def evidence_output_dir():
    root = Path(__file__).resolve().parents[1] / "artifacts" / "evidence_runs"
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir