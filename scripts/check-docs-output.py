"""Verify generated local file links that native Markdown validation can miss."""

from __future__ import annotations

import sys
import tomllib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


class FileLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.links.extend(value for key, value in attrs if key in {"href", "src"} and value)


def verify_site(site: Path, site_url: str, example: Path) -> None:
    """Check rendered file targets, not external URLs or semantic claims."""
    if not (site / "index.html").is_file():
        raise RuntimeError("Missing generated documentation home")
    if not example.is_file():
        raise RuntimeError(f"Missing required source example: {example}")
    published_example = site / example.name
    if not published_example.is_file() or published_example.read_bytes() != example.read_bytes():
        raise RuntimeError(f"Missing or changed generated example: {published_example}")

    base = urlsplit(site_url)
    for page in sorted(site.rglob("*.html")):
        parser = FileLinks()
        parser.feed(page.read_text(encoding="utf-8"))
        parser.close()
        page_url = urljoin(site_url, page.relative_to(site).as_posix())
        for link in parser.links:
            original = urlsplit(link)
            if original.scheme and original.scheme not in {"http", "https"}:
                continue
            resolved = urlsplit(urljoin(page_url, link))
            if resolved.netloc != base.netloc:
                continue  # External URL: do not fetch it.
            if not resolved.path.startswith(base.path):
                if original.netloc:
                    continue  # Absolute link to a different site on the same host.
                raise RuntimeError(f"{page}: link escapes project site: {link}")
            relative = unquote(resolved.path.removeprefix(base.path))
            target = (site / relative).resolve()
            if not target.is_relative_to(site.resolve()):
                raise RuntimeError(f"{page}: link escapes output directory: {link}")
            if resolved.path.endswith("/") or target.is_dir():
                target /= "index.html"
            if not target.is_file():
                raise RuntimeError(f"{page}: missing generated link target: {link}")


def main() -> int:
    try:
        with Path("zensical.toml").open("rb") as config:
            project = tomllib.load(config)["project"]
        site_url = project["site_url"]
        if site_url != "https://bio-comp.github.io/circuit-ci/":
            raise RuntimeError("Unexpected documentation site URL")
        validation = project["validation"]
        if (
            project.get("strict") is not True
            or validation.get("invalid_links") is not True
            or validation.get("invalid_link_anchors") is not True
        ):
            raise RuntimeError("Strict link and anchor validation must remain enabled")
        verify_site(Path("site"), site_url, Path("docs/example_state_psu.yaml"))
    except (OSError, ValueError, KeyError, RuntimeError, TypeError, AttributeError) as error:
        print(f"Documentation output check failed: {error}", file=sys.stderr)
        return 1
    print("Documentation output check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
