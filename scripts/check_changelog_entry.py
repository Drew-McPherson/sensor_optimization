from __future__ import annotations

from datetime import date
from pathlib import Path
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that CHANGELOG.md contains a required date marker and optional text."
    )
    parser.add_argument(
        "--changelog",
        default="CHANGELOG.md",
        help="Path to changelog file (default: CHANGELOG.md).",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Date token to require, e.g. 2026-07-31 (default: today).",
    )
    parser.add_argument(
        "--contains",
        action="append",
        default=[],
        help="Additional string that must appear in the changelog. Can be repeated.",
    )

    args = parser.parse_args()

    changelog_path = Path(args.changelog)
    if not changelog_path.exists():
        print(f"FAIL: changelog not found: {changelog_path}")
        return 1

    content = changelog_path.read_text(encoding="utf-8")

    missing = []
    if args.date not in content:
        missing.append(f"date token '{args.date}'")

    for token in args.contains:
        if token not in content:
            missing.append(f"text token '{token}'")

    if missing:
        print("FAIL: changelog validation failed.")
        for item in missing:
            print(f" - Missing {item}")
        return 2

    print("PASS: changelog validation succeeded.")
    print(f"Validated file: {changelog_path}")
    print(f"Found date token: {args.date}")
    if args.contains:
        print("Found required text tokens:")
        for token in args.contains:
            print(f" - {token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
