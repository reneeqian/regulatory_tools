from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import json
import os

@dataclass
class EvidenceIssue:
    level: str                  # ERROR | WARN | INFO
    message: str
    requirement_tag: str | None  # <-- ADD
    context: str | None = None


@dataclass
class EvidenceReport:
    subject: str
    test_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    issues: List[EvidenceIssue] = field(default_factory=list)
    requirements: set[str] = field(default_factory=set)
    requirement_provider: Optional[object] = None


    def error(self, message: str, requirement_tag: str | None, context: str | None = None):
        if requirement_tag:
            self.requirements.add(requirement_tag)
        self.issues.append(EvidenceIssue("ERROR", message, requirement_tag, context))

    def warn(self, message: str, requirement_tag: str | None, context: str | None = None):
        if requirement_tag:
            self.requirements.add(requirement_tag)
        self.issues.append(EvidenceIssue("WARN", message, requirement_tag, context))

    def info(self, message: str, requirement_tag: str | None, context: str | None = None):
        if requirement_tag:
            self.requirements.add(requirement_tag)
        self.issues.append(EvidenceIssue("INFO", message, requirement_tag, context))

    @property
    def result(self) -> str:
        return "FAIL" if self.has_errors else "PASS"

    @property
    def has_errors(self) -> bool:
        return any(i.level == "ERROR" for i in self.issues)

    def summary(self) -> str:
        lines = [f"Evidence report for {self.subject}"]
        for i in self.issues:
            prefix = f"[{i.level}]"
            ctx = f" ({i.context})" if i.context else ""
            lines.append(f"{prefix} {i.message}{ctx}")
        return "\n".join(lines)
    
    def to_string(self) -> str:
        """
        Human-readable string representation suitable for exceptions.
        """
        lines = [f"Evidence report for {self.subject}"]

        for i in self.issues:
            prefix = f"[{i.level}]"
            req = f" [{i.requirement_tag}]" if i.requirement_tag else ""
            ctx = f" ({i.context})" if i.context else ""
            lines.append(f"{prefix}{req} {i.message}{ctx}")

        return "\n".join(lines)
    
    def print_summary(self) -> None:
        errors   = [i for i in self.issues if i.level == "ERROR"]
        warnings = [i for i in self.issues if i.level == "WARN"]
        infos    = [i for i in self.issues if i.level == "INFO"]

        status = "❌ FAIL" if errors else "✅ PASS"

        print(f"\n╔══ Evidence Report: {self.subject} {'═' * max(0, 42 - len(self.subject))}╗")
        print(f"║  Status:   {status}")
        print(f"║  Errors:   {len(errors)}   Warnings: {len(warnings)}   Info: {len(infos)}")
        print(f"╚{'═' * 60}╝")

        def _render_group(issues, icon, label):
            if not issues:
                return

            # Group by message so repeated occurrences collapse into one row with a count
            from collections import defaultdict
            grouped = defaultdict(list)  # message -> [context, ...]
            for i in issues:
                grouped[i.message].append(i.context or "")

            print(f"\n  {icon} {label} ({len(issues)} total)")
            print(f"  {'─' * 58}")

            for msg, contexts in grouped.items():
                count = len(contexts)
                count_badge = f" ×{count}" if count > 1 else ""
                print(f"  {icon} {msg}{count_badge}")

                # Show up to 3 context lines; collapse the rest with a note
                show = contexts if count <= 4 else contexts[:3]
                for ctx in show:
                    if ctx:
                        # Truncate very long context strings
                        short = (ctx[:110] + "…") if len(ctx) > 110 else ctx
                        print(f"       ↳ {short}")
                if count > 4:
                    print(f"       ↳ … and {count - 3} more (see full report for details)")

        _render_group(errors,   "❌", "ERRORS")
        _render_group(warnings, "⚠️ ", "WARNINGS")
        # Info is intentionally suppressed in terminal output (too verbose)

        print(f"\n{'─' * 62}\n")
        
        
    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "subject": self.subject,
            "timestamp": self.timestamp.isoformat(),
            "result": self.result,
            "requirement_tags": sorted(self.requirements),   # 👈 keep this
            "requirements": sorted(self.resolve_requirement_ids()),  # 👈 resolved
            "issues": [
                {
                    "level": i.level,
                    "message": i.message,
                    "context": i.context,
                    "requirement_tag": i.requirement_tag,
                }
                for i in self.issues
            ],
        }

    def to_markdown(self) -> str:
        lines = [f"# Evidence Report: {self.subject}", ""]
        lines.append(f"**Test ID:** {self.test_id}")
        lines.append(f"**Result:** {self.result}")
        lines.append("")

        for i in self.issues:
            ctx = f" ({i.context})" if i.context else ""
            req = f" [Req: {i.requirement_tag}]" if i.requirement_tag else ""
            lines.append(f"- **{i.level}**{req}: {i.message}{ctx}")

        return "\n".join(lines)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_text(json.dumps(self.to_dict(), indent=2))
        elif path.suffix in {".md", ".markdown"}:
            path.write_text(self.to_markdown())
        else:
            raise ValueError(f"Unsupported report format: {path}")

    def auto_save(self, name: str, root: Path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = name.replace("::", "_").replace("/", "_")
        path = root / f"{safe_name}_{ts}.json"
        self.save(path)
    
    def merge(self, other: "EvidenceReport", prefix: str | None = None):
        """
        Merge another report into this one.
        Optionally prefix context (e.g., patient_id).
        """
        for issue in other.issues:
            context = issue.context

            if prefix:
                context = f"{prefix} | {context}" if context else prefix

            self.issues.append(
                EvidenceIssue(
                    level=issue.level,
                    message=issue.message,
                    requirement_tag=issue.requirement_tag,
                    context=context,
                )
            )

        self.requirements.update(other.requirements)
        
        
    def resolve_requirement_ids(self) -> set[str]:
        if not self.requirement_provider:
            return set()

        resolved = set()

        for tag in self.requirements:
            ids = self.requirement_provider.get_ids(tag) or []

            if not ids:
                # Optional but VERY useful
                print(f"[WARN] No requirement mapping for tag '{tag}'")

            resolved.update(ids)

        return resolved
        
def generate_evidence_summary(evidence_run_dir: Path) -> dict:
    """
    Aggregates evidence JSON files from a single evidence run directory.

    Returns summary statistics used by reporting and tests.
    """

    total = 0
    passed = 0
    failed = 0

    for record_file in evidence_run_dir.glob("*.json"):

        try:
            record = json.loads(record_file.read_text())
        except Exception:
            continue

        result = record.get("result")

        total += 1

        if result == "PASS":
            passed += 1
        elif result == "FAIL":
            failed += 1

    return {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
    }