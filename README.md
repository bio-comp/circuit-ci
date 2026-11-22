# Circuit-CI

**Circuit-CI** is an early experimental software foundation for evidence-driven
electronics feasibility and verification. It preserves the original design:
typed `CircuitState`, rule packs, findings, an audit record, and the `cci` CLI.

**NOT DESIGN-QUALIFIED.** The inherited PSU pack assumes voltage across a
resistor without establishing connectivity, and finding aggregation can
prioritize missing data over a hard failure. The op-amp pack uses component
names as proxy evidence of topology. Do **not** interpret `AUTO_PASS` or
a passing golden fixture as electrical safety or functional correctness.
See [rule safety issue #2](https://github.com/bio-comp/circuit-ci/issues/2).
The `ProposedChange` argument is accepted but **not applied**; see
[contract issue #3](https://github.com/bio-comp/circuit-ci/issues/3).

## Implemented today

- Pydantic v2 circuit-state and result models
- Experimental PSU and op-amp rule packs (not physically qualified)
- Typer `cci` and `circuitci` CLI entry points
- Two pytest golden-test functions covering four legacy examples

**Not implemented:** connectivity-aware analysis, architecture-feasibility
qualification, applied edits, DigiKey/KiCad Happy integration, SPICE execution,
physical measurement, production telemetry, or source-backed safety approval.
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
uv run --locked mypy circuit_ci
uv run --locked pytest --randomly-seed=42
uv run --locked pytest --randomly-seed=42 --cov=circuit_ci --cov-branch --cov-report=term-missing
uv build
```

`uv.lock` is committed. The branch-coverage gate is 85%, set below the
measured 87.93% on Python 3.11 and 3.13 with the new CLI/metadata tests.
The inherited two-test baseline covered 74%; do not lower the gate to conceal failures.

For fast pre-commit and full pre-push checks, install the single configured
`prek` hook manager **in a checkout with an isolated Git hook directory**:

```bash
uv run --locked prek validate-config .pre-commit-config.yaml
uv run --locked prek install --hook-type pre-commit --hook-type pre-push
```

Pre-push validation is intentionally scoped to a clean, single-ref push of
the current HEAD; unusual ref operations require independent SHA qualification.
CI independently runs the gates. These hooks are developer safeguards rather
than a security boundary.

## Engineering roadmap

GitHub [SX-001 issues](https://github.com/bio-comp/circuit-ci/issues)
track electrical rule repairs, typed state/proposed changes, explicitly
non-exporting Logfire diagnostics, hardware feasibility, DDR4 SO-DIMM
acceptance, and integrations. Prefer version-qualified KiCad Happy and
existing EDA tools over duplicating their circuit analysis. The statuses
`HARD_FAIL`, `MISSING_DATA`, `CONFLICT_REQUIRES_REVIEW`, and `AUTO_PASS`
are **legacy software outputs**, not stages of engineering qualification.
