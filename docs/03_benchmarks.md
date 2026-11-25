# Benchmarks — legacy fixtures and proposed evaluation

## What actually runs today

The repository contains **four legacy examples** in
`benchmarks/golden/psu_cases.yaml` and
`benchmarks/golden/opamp_cases.yaml`. Two pytest test functions evaluate
their expected rule identifiers and aggregate statuses. These tests exercise
the *existing software outputs*, not circuit topology correctness, calibrated
measurement results, or agreement with physical hardware.

The PSU legacy cases include an unsupported `Vin²/R1` dissipation
assumption. A passing test may therefore preserve an unsafe behavior; see
[issue #2](https://github.com/bio-comp/circuit-ci/issues/2).

## Proposed comparative benchmark — not performed

A future study **could** compare an LLM-only design-proposal baseline against
a constrained-edit, source-backed Circuit-CI feasibility/verification
workflow. Neither the LLM-only baseline nor the proposed full Circuit-CI
workflow has been implemented, measured, or compared in this repository.
There are **no empirical performance claims** to report.

Candidate metrics, all **unimplemented** as benchmark computations:

- `schema_valid_rate` — proportion satisfying a defined schema
- `hard_violation_rate` — independently established hard constraints violated
- `bluff_rate` — unsupported success claims despite missing prerequisites
- `staging_pass_rate` — qualified simulation-stage pass rate
- `iterations_to_pass` — count under a defined acceptance policy
- `review_friction` — defined number of conflicts and required measurements

Expanding to 30+ cases is a proposal, not a completed benchmark. Any future
benchmark must establish independently grounded known-good and known-bad
cases, measurement provenance and non-vacuous acceptance criteria.
