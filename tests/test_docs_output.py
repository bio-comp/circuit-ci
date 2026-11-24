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
    (tmp_path / "site" / "fallback.png").write_bytes(b"fixture")
    (tmp_path / "site" / "index.html").write_text(
        '<a href="guide/">Guide</a><a href="example_state_psu.yaml">Example</a>'
        '<a href="https://github.com/bio-comp/circuit-ci">Repository</a>'
        '<img src="fallback.png">',
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


@pytest.mark.parametrize(
    ("path", "markup"),
    [
        (
            "index.html",
            '<img src="images/plain.png" srcset="images/plain.png 1x, images/retina.png 2x">',
        ),
        ("index.html", '<img srcset="images/plain.png 320w,images/retina.png 640w" sizes="100vw">'),
        ("index.html", '<img srcset="images/plain.png, images/retina.png 2x">'),
        ("index.html", '<img srcset="images/with,comma.png 1x, images/retina.png 2x">'),
        ("index.html", '<img srcset="data:image/png;base64,AAAA 1x, images/retina.png 2x">'),
        ("index.html", '<img srcset="data:image/png;base64,AAAA, images/retina.png 2x">'),
        ("index.html", '<img srcset="https://example.org/a,b.png 1x, //cdn.example.org/b.png 2x">'),
        (
            "index.html",
            '<img srcset="blob:https://example.org/id 1x, data:image/svg+xml,%3Csvg%3E 2x">',
        ),
        ("index.html", '<img srcset="images/plain.png&#9;1x,&#10;images/retina.png 2x">'),
        (
            "guide/index.html",
            '<picture><source srcset="../images/retina.png 2x"><img src="/circuit-ci/images/plain.png"></picture>',
        ),
        ("guide/index.html", '<video poster="../images/plain.png?rev=1#frame" controls></video>'),
        (
            "guide/index.html",
            '<link rel="preload" as="image" imagesrcset="/circuit-ci/images/plain.png 1x, ../images/retina.png 2x">',
        ),
        (
            "guide/index.html",
            '<img srcset="https://BIO-COMP.github.io:443/circuit-ci/images/plain.png 1x, //bio-comp.github.io/circuit-ci/images/retina.png 2x">',
        ),
        (
            "index.html",
            '<video poster="https://example.org/poster.png"></video><video poster="data:image/png;base64,AAAA"></video>',
        ),
        (
            "index.html",
            '<img srcset="https://bio-comp.github.io/other/image.png 1x, https://bio-comp.github.io:8443/circuit-ci/external.png 2x"><a href="mailto:example@example.org">Mail</a>',
        ),
    ],
)
def test_valid_media(rendered_site: Path, path: str, markup: str) -> None:
    images = rendered_site / "site" / "images"
    images.mkdir()
    for name in ("plain.png", "retina.png", "with,comma.png"):
        (images / name).write_bytes(b"fixture")
    (rendered_site / "site" / path).write_text(markup, encoding="utf-8")
    result = check_output(rendered_site)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("path", "markup", "attribute", "missing"),
    [
        (
            "index.html",
            '<img src="fallback.png" srcset="missing-retina.png 2x">',
            "srcset",
            "missing-retina.png",
        ),
        (
            "index.html",
            '<img srcset="fallback.png 320w,missing.png 640w">',
            "srcset",
            "missing.png",
        ),
        (
            "index.html",
            '<img srcset="data:image/png;base64,AAAA 1x, missing.png 2x">',
            "srcset",
            "missing.png",
        ),
        (
            "index.html",
            '<img srcset="https://example.org/a,b.png 1x, missing.png 2x">',
            "srcset",
            "missing.png",
        ),
        ("index.html", '<img srcset="fallback.png, missing.png 2x">', "srcset", "missing.png"),
        ("index.html", '<img srcset="missing,comma.png 2x">', "srcset", "missing,comma.png"),
        (
            "guide/index.html",
            '<picture><source srcset="../missing.png 2x"><img src="../fallback.png"></picture>',
            "srcset",
            "../missing.png",
        ),
        (
            "index.html",
            '<video poster="missing-cover.png" controls></video>',
            "poster",
            "missing-cover.png",
        ),
        (
            "guide/index.html",
            '<video poster="/circuit-ci/missing-cover.png"></video>',
            "poster",
            "/circuit-ci/missing-cover.png",
        ),
        (
            "guide/index.html",
            '<link rel="preload" as="image" imagesrcset="../missing.png 2x">',
            "imagesrcset",
            "../missing.png",
        ),
        (
            "index.html",
            '<img srcset="https://BIO-COMP.github.io:443/circuit-ci/missing.png 2x">',
            "srcset",
            "https://BIO-COMP.github.io:443/circuit-ci/missing.png",
        ),
        (
            "index.html",
            '<img srcset="//bio-comp.github.io/circuit-ci/missing.png 2x">',
            "srcset",
            "//bio-comp.github.io/circuit-ci/missing.png",
        ),
    ],
)
def test_missing_media(
    rendered_site: Path, path: str, markup: str, attribute: str, missing: str
) -> None:
    (rendered_site / "site" / "fallback.png").write_bytes(b"fixture")
    (rendered_site / "site" / path).write_text(markup, encoding="utf-8")
    result = check_output(rendered_site)
    assert result.returncode == 1
    assert f"site/{path}: missing generated link target: {attribute}={missing!r}" in result.stderr


@pytest.mark.parametrize(
    ("markup", "diagnostic"),
    [
        ('<img srcset="../../outside.png 2x">', "link escapes project site"),
        ('<video poster="../%2e%2e/outside.png"></video>', "link escapes output directory"),
        ('<img srcset="../%2e%2e/outside.png 2x">', "link escapes output directory"),
    ],
)
def test_media_traversal(rendered_site: Path, markup: str, diagnostic: str) -> None:
    (rendered_site / "outside.png").write_bytes(b"outside")
    (rendered_site / "site" / "guide" / "index.html").write_text(markup, encoding="utf-8")
    result = check_output(rendered_site)
    assert result.returncode == 1
    assert diagnostic in result.stderr


def test_directory_index_symlink_escape(rendered_site: Path) -> None:
    outside = rendered_site / "outside.html"
    outside.write_text("outside", encoding="utf-8")
    index = rendered_site / "site" / "guide" / "index.html"
    index.unlink()
    index.symlink_to(outside)
    result = check_output(rendered_site)
    assert result.returncode == 1
    assert "link escapes output directory" in result.stderr
