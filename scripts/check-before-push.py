#!/usr/bin/env python3
"""Fail-closed local-first verification for ordinary single-HEAD pushes.

The same file is invoked as prek's supported pre-push.legacy hook, where it
receives *all* Git pre-push stdin ref updates, and as prek's full quality hook.
Do not infer the complete ref set from PRE_COMMIT_TO_REF: prek v0.5.11
deliberately selects only its first eligible ref.
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


def validate_ref_updates(payload: str, *, head: str, branch: str) -> None:
    """Accept one branch update sourced from HEAD; reject every other ref set.

    The Git pre-push hook contract sends four whitespace-delimited fields
    per outgoing ref. Rejections prevent partial publication of the set.
    """
    lines = payload.splitlines()
    if len(lines) != 1:
        raise RuntimeError(f"Expected exactly one outgoing ref, got {len(lines)}")
    fields = lines[0].split()
    if len(fields) != 4:
        raise RuntimeError("Malformed pre-push ref update")
    local_ref, local_sha, remote_ref, _remote_sha = fields
    if local_ref not in {"HEAD", f"refs/heads/{branch}"}:
        raise RuntimeError("Only current-branch/HEAD pushes are qualified")
    if local_sha != head:
        raise RuntimeError("Outgoing SHA differs from current HEAD")
    if not remote_ref.startswith("refs/heads/"):
        raise RuntimeError("Only branch destinations are qualified")


def require_ref_guard_installed() -> None:
    """Fail if prek was installed without its required complete-ref guard."""
    legacy_path = (
        Path(git("rev-parse", "--path-format=absolute", "--git-common-dir"))
        / "hooks"
        / "pre-push.legacy"
    )
    if not legacy_path.is_symlink() or legacy_path.resolve() != Path(__file__).resolve():
        raise RuntimeError(
            "Missing managed pre-push.legacy ref guard; run scripts/install-hooks.py"
        )
    if not os.access(legacy_path, os.X_OK):
        raise RuntimeError("Pre-push ref guard is not executable")


def check_clean_head() -> str:
    head = git("rev-parse", "HEAD")
    if not head:
        raise RuntimeError("Cannot resolve HEAD")
    if git("status", "--porcelain=v1", "--untracked-files=normal"):
        raise RuntimeError("Working tree is not clean; outgoing HEAD is not qualified")
    if os.environ.get("PREK_HOOK_STAGE") == "pre-push":
        require_ref_guard_installed()
        pushed_sha = os.environ.get("PRE_COMMIT_TO_REF")
        if not pushed_sha or pushed_sha != head:
            raise RuntimeError("Prek did not expose the expected outgoing HEAD SHA")
    return head


def full_gate() -> None:
    before = check_clean_head()
    print(f"Qualifying clean HEAD {before}", flush=True)
    for command in COMMANDS:
        print("+", " ".join(command), flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
    if check_clean_head() != before:
        raise RuntimeError("HEAD changed during qualification")
    print(f"QUALIFIED: {before}")


def ref_guard() -> None:
    # Git invokes the legacy hook with remote name/URL and complete refs on stdin.
    # Prek 0.5.11 forwards the raw Git stdin to this supported legacy hook.
    # It may skip the ordinary full hook when all outgoing commits already
    # exist on the remote; this guard must independently reject dirty trees.
    if git("status", "--porcelain=v1", "--untracked-files=normal"):
        raise RuntimeError("Working tree is not clean; refusing ref publication")
    updates = sys.stdin.read()
    validate_ref_updates(
        updates,
        head=git("rev-parse", "HEAD"),
        branch=git("symbolic-ref", "--quiet", "--short", "HEAD"),
    )
    print("REF GUARD: single current-HEAD branch update accepted", flush=True)


def main() -> int:
    try:
        if len(sys.argv) == 1:
            full_gate()
        elif len(sys.argv) == 3:
            ref_guard()
        else:
            raise RuntimeError("Expected no arguments or Git's remote name and URL")
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"NOT QUALIFIED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
