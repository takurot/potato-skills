#!/usr/bin/env python3
"""Validate generated potato-skills checksums and both host inventories."""

from __future__ import annotations

import argparse
from pathlib import Path

from build_skills import verify_generated_output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("skills"))
    args = parser.parse_args()
    try:
        verify_generated_output(args.output.resolve())
    except ValueError as error:
        parser.error(str(error))
    print(f"Validated Claude Code and Codex outputs in {args.output}")


if __name__ == "__main__":
    main()
