"""Pure negative controls for the pre-push stdin ref-set policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-before-push.py"
HEAD = "a" * 40
OLD = "b" * 40
ZERO = "0" * 40


def load_validator():
    spec = importlib.util.spec_from_file_location("push_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_ref_updates


def test_current_head_single_branch_is_accepted() -> None:
    validate = load_validator()
    validate(f"HEAD {HEAD} refs/heads/qualified {ZERO}\n", head=HEAD, branch="feature")


@pytest.mark.parametrize(
    "ref_lines",
    [
        "",
        f"HEAD {HEAD} refs/heads/qualified {ZERO}\nrefs/tags/old {OLD} refs/tags/old {ZERO}\n",
        f"HEAD {HEAD} refs/heads/qualified {ZERO}\nrefs/heads/old {OLD} refs/heads/old {ZERO}\n",
        f"refs/heads/feature {OLD} refs/heads/qualified {ZERO}\n",
        f"refs/tags/old {HEAD} refs/tags/old {ZERO}\n",
        f"(delete) {ZERO} refs/heads/qualified {HEAD}\n",
        f"HEAD {HEAD} refs/tags/a {ZERO}\n",
        f"HEAD {HEAD} refs/heads/qualified\n",
    ],
)
def test_unsupported_ref_sets_fail_closed(ref_lines: str) -> None:
    validate = load_validator()
    with pytest.raises(RuntimeError):
        validate(ref_lines, head=HEAD, branch="feature")
