from dataclasses import dataclass
from typing import Optional
from enum import Enum


class VerificationResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class TraceRow:
    """
    Represents one mapping between:
        Requirement → Test → Evidence → Result
    """

    requirement_id: str
    test_id: str
    evidence_file: Optional[str] = None
    result: Optional[VerificationResult] = None

    def is_verified(self) -> bool:
        return self.result == VerificationResult.PASS

    def is_failed(self) -> bool:
        return self.result == VerificationResult.FAIL
