"""Verify generated local file links that native Markdown validation can miss."""

from __future__ import annotations

import sys
import tomllib
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ASCII_WHITESPACE = " \t\n\r\f"


def srcset_urls(value: str) -> Iterator[str]:
    """Extract candidate URLs, not validate descriptor conformance.

    Follow the URL and descriptor token boundaries in the HTML Standard's
    srcset parsing algorithm. A comma inside a URL is not a separator.
    Conservatively check URLs even when their descriptors are malformed.
    """
    position = 0
    while position < len(value):
        while position < len(value) and value[position] in ASCII_WHITESPACE + ",":
            position += 1
        start = position
        while position < len(value) and value[position] not in ASCII_WHITESPACE:
            position += 1
        url = value[start:position]
        if not url:
            break
        yield url.rstrip(",")
        if url.endswith(","):
            continue

        # Consume descriptors until the next separator outside parentheses.
        in_parens = False
        while position < len(value):
            char = value[position]
            position += 1
            if char == "," and not in_parens:
                break
            if char == "(":
                in_parens = True
            elif char == ")":
                in_parens = False


class FileLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if not value:
                continue
            if key in {"href", "src"} or (tag, key) == ("video", "poster"):
                self.links.append((key, value))
            elif (key == "srcset" and tag in {"img", "source"}) or (
                tag == "link" and key == "imagesrcset"
            ):
                self.links.extend((key, url) for url in srcset_urls(value))


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
        for attribute, link in parser.links:
            original = urlsplit(link)
            if original.scheme and original.scheme not in {"http", "https"}:
                continue
            resolved = urlsplit(urljoin(page_url, link))
            if resolved.hostname != base.hostname or (
                resolved.port is not None
                and resolved.port != (443 if resolved.scheme == "https" else 80)
            ):
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
                target = (target / "index.html").resolve()
                if not target.is_relative_to(site.resolve()):
                    raise RuntimeError(f"{page}: link escapes output directory: {link}")
            if not target.is_file():
                raise RuntimeError(
                    f"{page}: missing generated link target: {attribute}={link!r} ({target})"
                )


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
