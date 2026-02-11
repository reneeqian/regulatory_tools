from pathlib import Path
from regulatory_tools.traceability.generator import generate_trace_rows, write_markdown

def main():
    print("🔍 Generating traceability matrix...")

    rows = generate_trace_rows(
        evidence_root=Path("artifacts/evidence_runs")
    )
    print(f"Found {len(rows)} trace rows")

    output_path = Path("docs/traceability.md")
    write_markdown(
        rows,
        output=output_path
    )
    print(f"✅ Traceability matrix written to {output_path.resolve()}")


if __name__ == "__main__":
    main()
