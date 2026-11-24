"""Known-good and known-bad generated documentation file-link controls."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-docs-output.py"


@pytest.fixture
def rendered_site(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "site" / "guide").mkdir(parents=True)
    (tmp_path / "zensical.toml").write_text(
        '[project]\nsite_url = "https://bio-comp.github.io/circuit-ci/"\n'
        "strict = true\n[project.validation]\n"
        "invalid_links = true\ninvalid_link_anchors = true\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "example_state_psu.yaml").write_text("example: true\n")
    (tmp_path / "site" / "example_state_psu.yaml").write_text("example: true\n")
    (tmp_path / "site" / "index.html").write_text(
        '<a href="guide/">Guide</a><a href="example_state_psu.yaml">Example</a>'
        '<a href="https://github.com/bio-comp/circuit-ci">Repository</a>',
        encoding="utf-8",
    )
    (tmp_path / "site" / "guide" / "index.html").write_text(
        '<a href="../">Home</a><a href="/circuit-ci/example_state_psu.yaml">Example</a>',
        encoding="utf-8",
    )
    return tmp_path


def check_output(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_valid_site(rendered_site: Path) -> None:
    result = check_output(rendered_site)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("path", "content", "diagnostic"),
    [
        ("site/index.html", None, "Missing generated documentation home"),
        ("docs/example_state_psu.yaml", None, "Missing required source example"),
        ("site/example_state_psu.yaml", None, "Missing or changed generated example"),
        ("site/example_state_psu.yaml", "wrong: true", "Missing or changed generated example"),
        ("site/index.html", '<a href="missing.yaml">Example</a>', "missing generated link target"),
        ("site/guide/index.html", '<a href="../../">Escape</a>', "link escapes project site"),
        ("site/index.html", '<script src="missing.js"></script>', "missing generated link target"),
    ],
)
def test_invalid_site(rendered_site: Path, path: str, content: str | None, diagnostic: str) -> None:
    target = rendered_site / path
    if content is None:
        target.unlink()
    else:
        target.write_text(content, encoding="utf-8")
    result = check_output(rendered_site)
    assert result.returncode != 0
    assert diagnostic in result.stderr


@pytest.mark.parametrize("flag", ["strict", "invalid_links", "invalid_link_anchors"])
def test_disabled_validation(rendered_site: Path, flag: str) -> None:
    config = rendered_site / "zensical.toml"
    config.write_text(config.read_text().replace(f"{flag} = true", f"{flag} = false"))
    result = check_output(rendered_site)
    assert result.returncode != 0
    assert "Strict link and anchor validation must remain enabled" in result.stderr


def test_wrong_site_url(rendered_site: Path) -> None:
    config = rendered_site / "zensical.toml"
    config.write_text(config.read_text().replace("/circuit-ci/", "/other/"))
    result = check_output(rendered_site)
    assert result.returncode != 0
    assert "Unexpected documentation site URL" in result.stderr
