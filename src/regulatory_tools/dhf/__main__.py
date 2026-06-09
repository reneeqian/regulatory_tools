"""CLI entry point: python -m regulatory_tools.dhf <dhf_root> [--base-dir <path>]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from regulatory_tools.dhf.generator import DHFGenerator
from regulatory_tools.dhf.validator import DHFValidationError


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="regulatory-generate-dhf",
        description="Regenerate all DHF documents from source YAML files.",
    )
    parser.add_argument(
        "dhf_root",
        type=Path,
        help="Path to the DHF/docs repository root (where dhf_context.yaml lives).",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Primary code repository root. Relative paths in dhf_context.yaml "
            "are resolved against this directory."
        ),
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        metavar="FILE",
        help="Context filename relative to dhf_root (default: dhf_context.yaml).",
    )
    args = parser.parse_args()

    dhf_root: Path = args.dhf_root.resolve()
    context_file: Path = dhf_root / (args.context or Path("dhf_context.yaml"))
    base_dir: Path | None = args.base_dir.resolve() if args.base_dir else None

    if not context_file.exists():
        print(f"error: dhf_context.yaml not found at {context_file}", file=sys.stderr)
        sys.exit(1)

    try:
        generator = DHFGenerator.from_config(dhf_root, context_file, base_dir=base_dir)
    except DHFValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    report = generator.run_all()

    print(json.dumps({
        "files_modified": [str(p) for p in report.files_modified],
        "unfilled_vars": [[str(p), var] for p, var in report.unfilled_vars],
        "scaffolded_sections": [str(p) for p in report.scaffolded_sections],
    }))


if __name__ == "__main__":
    main()
