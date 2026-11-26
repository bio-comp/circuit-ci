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

### YAML input contract

The input is a single UTF-8 YAML document. Mapping keys must resolve to
strings under PyYAML's safe resolver (quote keys such as numeric-looking
component IDs or YAML 1.1 boolean-like words). Keys must be unique within
each mapping, at every depth, even when repeated values are identical.
Ordinary anchors and aliases are permitted subject to the state schema;
each referenced mapping is checked before safe construction. Merge keys
(`<<` with the YAML merge tag), non-string or complex keys, and special
collection tags such as `!!omap`, `!!pairs` and `!!set` are rejected.
A quoted literal string key `"<<"` is not a merge instruction.

Ambiguous or malformed YAML is an input error (exit 2, diagnostic on stderr,
no verdict JSON). No output file is created or overwritten on input
validation failure; an existing file is unchanged and must not be mistaken
for a result of the failed invocation. Safe construction is followed by
the existing Pydantic state validation, including strict nested evidence
models. Unknown outer state fields can still be ignored (including a
misspelled `missing_prerequisites`); broader state validation belongs to
[issue #3](https://github.com/bio-comp/circuit-ci/issues/3).


**Critical process-exit limitation:** The current implementation can emit
`{"status": "HARD_FAIL", ...}` while the process exits **0**. This makes
`cci` a *JSON reporter*, not a safe shell/CI policy gate: `set -e` and
a passing command exit status do not mean the design passed. Consumers must
parse and evaluate the JSON verdict themselves. The illustrative YAML above
returns MISSING_DATA because it supplies no scoped rule evidence. See the
[rule evidence contract](01_architecture.md); statuses are not design-qualified. The future reporter-vs-gate semantics
and fail-closed exit contract belong to
[issue #12](https://github.com/bio-comp/circuit-ci/issues/12);
the current documentation does not change CLI exit-code behavior.

Planned, not implemented: `cci lint`, `cci verify`, and `cci report`.
Applying `ProposedChange`, running SPICE, and creating a measurement plan
are also **not** supported by the current CLI.
