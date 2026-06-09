"""CLI entry point: python -m regulatory_tools.summary <project_root> [--output path]"""

from __future__ import annotations

import argparse
from pathlib import Path

from regulatory_tools.summary.generator import generate_project_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a project status summary Markdown file.")
    parser.add_argument("project_root", type=Path, help="Root directory of the target project")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: <project_root>/project_summary.md)",
    )
    args = parser.parse_args()

    out = generate_project_summary(args.project_root.resolve(), args.output)
    print(f"Summary written to: {out}")


if __name__ == "__main__":
    main()
