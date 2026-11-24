# Development and review

## Locked development

From the repository root, use uv with the checked-in lockfile. Python 3.11
and 3.13 are the CI compatibility matrix; local development defaults to 3.13.

```bash
uv lock --check
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy circuit_ci scripts/check-docs-output.py
uv run --locked pytest --randomly-seed=42 --cov=circuit_ci --cov-branch --cov-report=term-missing
uv run --locked zensical build --clean
uv run --locked python scripts/check-docs-output.py
uv build
```

The documentation build uses strict internal Markdown link and anchor
validation. The output check verifies local file targets in generated HTML
`href`, `src`, image/source `srcset`, link `imagesrcset`, and video `poster`
attributes, plus the required published YAML example. It does not fetch external
URLs or validate image descriptor conformance, media decoding, CSS URLs,
JavaScript-generated requests, embedded documents, or custom HTML base URLs.
Use normal project-relative links; review other resource mechanisms explicitly.
Generated pages are in `site/`. Preview locally with
`uv run --locked zensical serve`. Neither link validation nor a successful
Python test establishes electrical correctness.

## Hooks and CI

In a standalone clone, install the existing complete-ref guard and prek hooks
using `uv run --locked python scripts/install-hooks.py`. Do not install
shared hooks from a linked worktree. The full pre-push gate includes the
locked documentation build; the staged pre-commit checks remain lightweight.

The independent PR check `documentation` builds the site without deployment
permissions. Main-only Pages publication uses the `github-pages` deployment
environment. Publication and required-check registration must be verified
separately from the build.

## Review contract

For every PR, record the documentation paths inspected, any changes or
evidence-based no-change rationale, verification of CLI/schema examples
against code, the local build result, and the observed PR documentation
check result. A changed interface requires a human audit even when the build
passes. Do not merge or close the owning issue without the documentation audit
and applicable verification gates.

## Privacy and evidence

The site uses system fonts and does not configure analytics or external
comments. Do not include private inventory, credentials, or unpublished
measurement data in public documentation. A software regression test, a
simulation, and a physical measurement are distinct evidence levels. Record
revision, conditions, limitations, and provenance before claiming any of them.
