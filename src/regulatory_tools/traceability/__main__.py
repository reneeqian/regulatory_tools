import sys
from pathlib import Path

from .pipeline import generate_traceability_matrix


def main():

    if len(sys.argv) != 2:
        print("Usage: python -m regulatory_tools.traceability <project_root>")
        sys.exit(1)

    project_root = Path(sys.argv[1])

    generate_traceability_matrix(project_root)


if __name__ == "__main__":
    main()
