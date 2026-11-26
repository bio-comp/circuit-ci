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

## Research coverage command

Run the bundled **synthetic** example from the repository root:

```bash
uv run --locked python -m circuit_ci.coverage_gate --policy benchmarks/coverage/policy.json --manifest benchmarks/coverage/manifest.json --receipts benchmarks/coverage/receipts.json
```

A trusted caller supplies a fresh run ID, exact subject and revision, and a
nonempty policy listing every mandatory claim/source pair. The policy owner
assigns stable source identities that identify the document and revision.
Supply observed receipts through a separate, access-controlled channel from the
collector. The agent can supply the manifest. If the agent can author or replay
all three inputs, this command offers no independent evidence of live access.

For each pair, the checker matches the run, subject, revision, source, receipt
ID, SHA-256 of the preserved UTF-8 body text, and literal passage. Hash the
collector's exact text extraction, including whitespace. Record the actual
source identity after redirects. Preserve the original artifact and extraction
method separately when verification depends on images, PDFs or tables. Partial
reads, blocked requests, negative searches, citations alone and self-reports
leave required coverage incomplete. The checker cannot authenticate authors,
authorize exclusions, infer relevance or verify that a passage supports a claim.
An independent reviewer still evaluates applicability, conflicts and meaning.

Exit **0** reports `COVERAGE_MET`. Exit **1** reports `COVERAGE_INCOMPLETE`
with per-claim/source reasons. Exit **2** denotes invalid input or usage.
These outcomes describe the supplied evidence packet only. Physical qualification
requires its own procedures and measurements.
