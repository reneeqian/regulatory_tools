from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TraceRow:
    requirement_id: str
    test_id: str
    evidence_file: Optional[str]
    result: Optional[str]
