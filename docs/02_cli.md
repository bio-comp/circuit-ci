# CLI — current reporter behavior and limits

The implemented command is the single root-level Typer invocation, available
as both `cci` and `circuitci`. A named `lint` subcommand is **not** currently
implemented:

```bash
uv run --locked cci docs/example_state_psu.yaml --pack psu
uv run --locked circuitci docs/example_state_psu.yaml --pack opamp
uv run --locked cci docs/example_state_psu.yaml --pack psu --out result.json
```

The CLI parses YAML into `CircuitState`, executes the selected *experimental*
PSU or op-amp rule pack, and writes `LinterResult` JSON to stdout unless
`--out` is provided. When `--out` is used, stdout reports the output path.
Unrecognized rule-pack names and invalid/missing inputs are CLI errors.

**Critical process-exit limitation:** The current implementation can emit
`{"status": "HARD_FAIL", ...}` while the process exits **0**. This makes
`cci` a *JSON reporter*, not a safe shell/CI policy gate: `set -e` and
a passing command exit status do not mean the design passed. Consumers must
parse and evaluate the JSON verdict themselves, remembering that the inherited
rules/statuses are not design-qualified. The future reporter-vs-gate semantics
and fail-closed exit contract belong to
[issue #12](https://github.com/bio-comp/circuit-ci/issues/12);
the current documentation does not change CLI exit-code behavior.

Planned, not implemented: `cci lint`, `cci verify`, and `cci report`.
Applying `ProposedChange`, running SPICE, and creating a measurement plan
are also **not** supported by the current CLI.
