from dataclasses import dataclass
from typing import List
from enum import Enum


class VerificationResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNTESTED = "UNTESTED"


@dataclass
class RequirementTraceEntry:
    requirement_id: str
    description: str
    tests: List[str]
    evidence_files: List[str]
    status: VerificationResult
