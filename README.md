# Circuit-CI

**Circuit-CI** is an early experimental software foundation for evidence-driven
electronics feasibility and verification. It preserves the original design:
typed `CircuitState`, rule packs, findings, an audit record, and the `cci` CLI.

**NOT DESIGN-QUALIFIED.** The PSU and op-amp packs now require explicit,
scoped caller-supplied evidence; unsupported or incomplete checks return
`MISSING_DATA`. Confirmed violations within supported declared conditions
take precedence over missing evidence. `AUTO_PASS` means only that all
mandatory checks in the selected experimental pack completed without findings,
not that a circuit is safe or functional. See the
[rule evidence contract](docs/01_architecture.md) and
[rule safety issue #2](https://github.com/bio-comp/circuit-ci/issues/2).
The `ProposedChange` argument is accepted but **not applied**; see
[contract issue #3](https://github.com/bio-comp/circuit-ci/issues/3).

## Implemented today

- Pydantic v2 circuit-state and result models
- Experimental PSU and op-amp rule packs (not physically qualified)
- Typer `cci` and `circuitci` CLI entry points
- Four legacy examples plus deterministic conditional-rule regressions

**Not implemented:** connectivity-aware analysis, architecture-feasibility
qualification, applied edits, DigiKey/KiCad Happy integration, SPICE execution,
measurement-plan generation/execution, physical measurement, production
telemetry, or source-backed safety approval.

**CLI warning:** a successful `cci` process exit is currently only a reporting
success. In particular, a JSON `HARD_FAIL` verdict can return shell exit code
**0**. A shell/CI caller must explicitly parse the JSON and apply its own
policy; it must not use the current CLI as a fail-closed design gate. The
reporter/gate exit contract is owned by
[issue #12](https://github.com/bio-comp/circuit-ci/issues/12).
Invalid or ambiguous YAML is rejected before rule evaluation; no result is
written. Mapping keys must be unique strings and YAML merge keys are
unsupported. See the [CLI YAML input contract](docs/02_cli.md#yaml-input-contract)
for alias handling, rejected constructs, and remaining outer-state validation
limitations (#3).

The original `staging` and `telemetry` files are placeholders.

## Reproducible development

Use [uv](https://docs.astral.sh/uv/); Poetry and pip-based project
workflows are not used. The supported distribution declares Python `>=3.11`;
local development is pinned to Python `3.13` in `.python-version`.

```bash
uv sync --locked
uv run --locked cci --help
uv run --locked circuitci --help
uv run --locked cci docs/example_state_psu.yaml --pack psu
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy circuit_ci scripts/check-docs-output.py
uv run --locked pytest --randomly-seed=42
uv run --locked pytest --randomly-seed=42 --cov=circuit_ci --cov-branch --cov-report=term-missing
uv run --locked zensical build --clean
uv run --locked python scripts/check-docs-output.py
uv build
```

`uv.lock` is committed. The branch-coverage gate is 85%, set below the
measured 87.93% on Python 3.11 and 3.13 with the new CLI/metadata tests.
The inherited two-test baseline covered 74%; do not lower the gate to conceal failures.

For fast pre-commit and full pre-push checks in a **standalone clone with its
own Git hook directory**, run:

```bash
uv run --locked prek validate-config .pre-commit-config.yaml
uv run --locked python scripts/install-hooks.py
```

This installs **prek** as the single hook manager and a small complete-ref
validator through prek's supported `pre-push.legacy` hook interface. Its
installation refuses linked worktrees (whose hook directory is shared) and
refuses to overwrite any existing unrelated legacy hook. Running `prek
install` **alone is insufficient**: the full pre-push gate fails closed if
the ref-set guard is missing. The guard accepts only a clean current-HEAD
single branch push; tags, deletions, additional refs and non-HEAD sources
are rejected, not silently skipped. For outgoing commits that require checking, prek then runs the full local
Ruff/mypy/pytest/coverage/documentation/packaging gate. Prek can skip that full stage when
Git recognizes all commits as already present on the remote; the legacy guard
still independently validates the complete ref set and clean worktree.
Hooks can be bypassed and are not a security boundary; GitHub CI independently
runs the quality gates.

The CI matrix sets `UV_PYTHON` for every uv operation and asserts the
**actual** interpreter rather than trusting the matrix job label.

## Documentation

Build the maintained Zensical site locally with
`uv run --locked zensical build --clean` (output: `site/`).
See [documentation home](docs/index.md) and the
[development and review contract](docs/development.md). The intended public
site is https://bio-comp.github.io/circuit-ci/. The output checker rejects
missing local file targets and a missing or changed published YAML example;
a successful local build is not evidence of public deployment.

## Engineering roadmap

GitHub [SX-001 issues](https://github.com/bio-comp/circuit-ci/issues)
track electrical rule repairs, typed state/proposed changes, explicitly
non-exporting Logfire diagnostics, hardware feasibility, DDR4 SO-DIMM
acceptance, and integrations. Prefer version-qualified KiCad Happy and
existing EDA tools over duplicating their circuit analysis. The statuses
`HARD_FAIL`, `MISSING_DATA`, `CONFLICT_REQUIRES_REVIEW`, and `AUTO_PASS`
are **legacy software outputs**, not stages of engineering qualification.
