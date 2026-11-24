# Circuit-CI

**Experimental software — not design-qualified.** Circuit-CI aims to support
evidence-driven electronics engineering. Current rule-pack results cannot
establish electrical safety or functional correctness.

## What is available

The current foundation provides Pydantic circuit-state and result models,
experimental PSU and op-amp rule packs, the `cci` and `circuitci` JSON
reporters, and four legacy golden examples. The development environment uses
uv, Ruff, mypy, pytest with branch coverage, and prek.

Start with the [CLI reference](02_cli.md) and the
[illustrative YAML input](example_state_psu.yaml). Do not energize or build
a circuit based on this example. A JSON `HARD_FAIL` can still return process
exit code zero; see [issue #12](https://github.com/bio-comp/circuit-ci/issues/12).

## What is not available

Connectivity-aware design decisions, applied `ProposedChange` verification,
executable SPICE staging, measurement-plan execution, WaveForms verification,
DigiKey and KiCad Happy adapters, architecture-feasibility/build-readiness
assessment, and physical electrical safety qualification are not implemented
or qualified.

Read the [thesis](00_thesis.md), [architecture](01_architecture.md), and
[benchmark limitations](03_benchmarks.md) for the distinction between current
behavior and intended capabilities. See [development and review](development.md)
for the software verification contract.

The [GitHub issue tracker](https://github.com/bio-comp/circuit-ci/issues)
is authoritative for implementation scope and open defects.
