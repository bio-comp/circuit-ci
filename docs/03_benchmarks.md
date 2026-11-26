# Benchmarks — legacy fixtures and proposed evaluation

## What actually runs today

The repository contains **four legacy examples** in
`benchmarks/golden/psu_cases.yaml` and
`benchmarks/golden/opamp_cases.yaml`. Two pytest test functions evaluate
their expected rule identifiers and aggregate statuses. These tests exercise
the *existing software outputs*, not circuit topology correctness, calibrated
measurement results, or agreement with physical hardware.

The four original input states are preserved. Their legacy expected outcomes
were corrected to MISSING_DATA: PSU-01 had assumed full input voltage across
R1, PSU-02 inferred terminal voltage from a target, OP-01 inferred missing
bias return from a name, and OP-02 inferred absent decoupling from an incomplete
component list. Expected findings are now checked exactly and in order.
The new `tests/test_rule_safety.py` suite independently exercises explicit
conditional clean/overstress/unknown cases, precedence, malformed values,
and deterministic findings, including the 12 V ideal divider counterexample
and a generated rating-order property test. See the
[rule evidence contract](01_architecture.md) for sources and limitations.

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

## Two embedded build cases

The examples under `examples/build_cases/` contain separate display and SPD reader
sketches, host-side protocol tests and a replay against the installed `cci` reporter.
Run these from a checkout with the project's locked Python environment. The host tests
require a C++17 compiler, Bash, Node.js and Python 3 and use synthetic inputs.

```bash
bash examples/build_cases/check-hosts.sh
uv run --locked python examples/build_cases/replay.py
```

The display parser requires three distinct IPv4 configuration fields. The sketch
accepts a reading only after the UART modem completes its response. Its U138 source
describes its own interface. Cached addresses do not establish a live route or
visibility into other switch ports. An offline Proxmox guest-card oracle checks permission-filtered synthetic responses
and a 60-second freshness boundary. Its transport result and status are test
inputs. It performs no network I/O and adds no telemetry screen to the device.
The SPD reader exercises page selection, read
pointers, two full reads and two CRCs. Its synthetic 4,096 MiB, 1Rx8 fixture declares
833 ps tCK. Its DRAM array remains untested even when every host assertion passes.

The replay projects nine display requirements and ten SPD requirements onto the legacy
PSU input. Each input declares a missing prerequisite. The expected software verdict
for this projection is `MISSING_DATA`. The command prints case ID, input SHA-256,
reporter exit code and status. Its own exit code is 0 for agreement on all cases, 1
for any unexpected verdict, or 2 if the reporter or its output cannot be used.
Main revision `bb15beaaadab615c026784e2f67c9aa01ca53755` returned `AUTO_PASS`
and shell exit 0 on all 19. This is reproducible evidence of a rule defect, independent
of the separate firmware parser checks. These projections contain no electrical netlist,
power measurement, genuine network telemetry or captured DIMM data.

See issues [#23](https://github.com/bio-comp/circuit-ci/issues/23) and
[#6](https://github.com/bio-comp/circuit-ci/issues/6) for engineering acceptance.
Physical build commissioning, native design packs and secure service telemetry remain
separate work.
