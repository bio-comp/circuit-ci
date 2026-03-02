# Circuit-CI architecture (v0)

Pipeline:
1) `StateBuilder` creates `CircuitState(v)`
2) `Proposer` emits `ProposedChange` (schema-only)
3) `Verifier` runs pack rules -> `Findings`
4) `Router` maps findings to `LinterResult.status`
5) (optional) `Staging` runs SPICE
6) if uncertain/marginal -> emit `MeasurementPlan`

In v0, staging is a hook; deterministic lint + routing is the core.
