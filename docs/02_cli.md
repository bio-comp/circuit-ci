# CLI

Primary executable: `cci` (alias: `circuitci`).

**Currently implemented:** the single Typer command is exposed at the
executable root. Run:

```bash
uv run --locked cci docs/example_state_psu.yaml --pack psu
uv run --locked cci docs/example_state_psu.yaml --pack opamp --out result.json
```

`cci lint --pack psu state.yaml` is **not currently implemented as a named
subcommand**. The original documentation described it as implemented, but
Typer's single-command behavior exposes the state argument at the root.
The compatibility decision for introducing named subcommands is tracked
alongside the state/verification contract work in issue #3.

Proposed later commands: `cci lint`, `cci verify`, `cci report`.
A CLI verdict from the inherited packs is not evidence of design safety.
