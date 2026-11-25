# Thesis — intended direction versus current implementation

**DomainOps = CI/CD for Decisions** is the motivating concept, not a claim
that Circuit-CI currently qualifies hardware.

## Implemented experimental foundation

- Pydantic v2 `CircuitState`, `ProposedChange`, `Finding`, `LinterResult`,
  `AuditPacket`, and `MeasurementPlan` **schemas**
- Two deterministic but **unqualified** rule packs (PSU and op-amp)
- Legacy finding/status aggregation and a Typer CLI that emits result JSON
- Four legacy golden examples exercised by two pytest test functions

These checks have known unsafe assumptions; neither `AUTO_PASS` nor a passing
golden example is evidence of electrical design verification. See
[issue #2](https://github.com/bio-comp/circuit-ci/issues/2).

## Proposed, not implemented

- A controlled action API that **applies** edits to a prior state. The current
  `ProposedChange` type exists, but rule-pack `plan` parameters are ignored
  ([issue #3](https://github.com/bio-comp/circuit-ci/issues/3)).
- Connectivity-aware circuit checks and sourced feasibility judgments
- Actual SPICE staging or simulator execution (present module is a placeholder)
- Generation, execution, and qualification of physical measurement plans
  (the current `MeasurementPlan` is a schema only)
- Structured operational diagnostics/tracing (telemetry module is a placeholder)
- Comparisons to LLM-only design proposals or production telemetry

The intended platform should distinguish *plausible, feasible, implemented,
simulated, physically measured*, with explicit evidence for each label.
None of these words is conferred by a current status enum.
