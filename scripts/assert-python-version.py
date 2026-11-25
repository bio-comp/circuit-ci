"""Fail if the effective Python interpreter differs from the CI matrix cell."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected", help="Expected Python major.minor, e.g. 3.11")
    args = parser.parse_args()
    expected = tuple(int(part) for part in args.expected.split("."))
    actual = sys.version_info[:2]
    print(f"Python matrix assertion: expected={expected}, actual={actual}", flush=True)
    print(f"Interpreter: {sys.executable}", flush=True)
    print(f"Runtime: {sys.version}", flush=True)
    if actual != expected:
        print("ERROR: Python matrix interpreter mismatch", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
