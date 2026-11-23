"""Install prek hooks plus its supported legacy ref-set guard in a standalone clone.

Never change Git hooks shared by other worktrees or overwrite unowned hooks.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "check-before-push.py"


def git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def main() -> None:
    git_dir = Path(git("rev-parse", "--path-format=absolute", "--git-dir")).resolve()
    common_dir = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if git_dir != common_dir:
        raise RuntimeError("Refusing to install shared Git hooks from a linked worktree")
    legacy = (
        Path(git("rev-parse", "--path-format=absolute", "--git-common-dir"))
        / "hooks"
        / "pre-push.legacy"
    )
    if legacy.is_symlink() and legacy.resolve() == GUARD.resolve():
        pass
    elif legacy.exists() or legacy.is_symlink():
        raise RuntimeError(f"Existing legacy hook must be preserved: {legacy}")
    if not GUARD.is_file() or not os.access(GUARD, os.X_OK):
        raise RuntimeError("Ref guard source must exist and be executable")
    subprocess.run(
        (
            "uv",
            "run",
            "--locked",
            "prek",
            "install",
            "--hook-type",
            "pre-commit",
            "--hook-type",
            "pre-push",
        ),
        cwd=ROOT,
        check=True,
    )
    if not legacy.is_symlink():
        legacy.symlink_to(GUARD)
    if legacy.resolve() != GUARD.resolve():
        raise RuntimeError("Ref-guard installation failed")
    print(f"Verified prek pre-push ref guard: {legacy}")


if __name__ == "__main__":
    main()
