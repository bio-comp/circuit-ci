"""Fail-closed local qualification of the clean current HEAD.

This gate is restricted to a single current-HEAD ref push. CI remains authoritative
for GitHub-side verification; hooks are bypassable developer safeguards.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMMANDS: tuple[tuple[str, ...], ...] = (
    ("uv", "lock", "--check"),
    ("uv", "sync", "--locked"),
    ("uv", "run", "--locked", "ruff", "check", "."),
    ("uv", "run", "--locked", "ruff", "format", "--check", "."),
    ("uv", "run", "--locked", "mypy", "circuit_ci"),
    (
        "uv",
        "run",
        "--locked",
        "pytest",
        "--randomly-seed=42",
        "--cov=circuit_ci",
        "--cov-branch",
        "--cov-report=term-missing",
    ),
    ("uv", "run", "--locked", "cci", "--help"),
    ("uv", "run", "--locked", "circuitci", "--help"),
    ("uv", "build"),
)


def git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def check_clean_head() -> str:
    head = git("rev-parse", "HEAD")
    if not head:
        raise RuntimeError("Cannot resolve HEAD")
    if git("status", "--porcelain=v1", "--untracked-files=normal"):
        raise RuntimeError("Working tree is not clean; outgoing HEAD is not qualified")
    # In pre-push, PRE_COMMIT_TO_REF is the *local* SHA being published;
    # PRE_COMMIT_FROM_REF is the remote SHA before the push (or zeroes).
    # This hook covers a single current-HEAD push; other refs need independent checks.
    if os.environ.get("PREK_HOOK_STAGE") == "pre-push" and not os.environ.get("PRE_COMMIT_TO_REF"):
        raise RuntimeError("Pre-push hook did not supply the outgoing SHA")
    pushed_sha = os.environ.get("PRE_COMMIT_TO_REF")
    if pushed_sha and pushed_sha != head:
        raise RuntimeError("Outgoing SHA differs from the clean checked-out HEAD")
    return head


def main() -> int:
    try:
        before = check_clean_head()
        print(f"Qualifying clean HEAD {before}", flush=True)
        for command in COMMANDS:
            print("+", " ".join(command), flush=True)
            subprocess.run(command, cwd=ROOT, check=True)
        after = check_clean_head()
        if after != before:
            raise RuntimeError("HEAD changed during qualification")
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"NOT QUALIFIED: {error}", file=sys.stderr)
        return 1
    print(f"QUALIFIED: {before}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
