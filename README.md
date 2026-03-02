# Circuit-CI

**Circuit-CI** is **CI/CD for circuits**.

Given a typed `CircuitState(v)` and a schema-only `ProposedChange` (edits, not essays), Circuit-CI:

1) runs fast deterministic **lint/compile** checks (ratings, ERC-ish rules, physics gates)
2) optionally runs **staging** (SPICE hooks)
3) **routes ambiguity** into a **MeasurementPlan** (production telemetry) instead of bluffing

The goal: stop "looks plausible" hardware from escaping into reality without evidence.

## Quickstart

```bash
pip install -e .
cci --help

# run golden tests
pip install -e '.[dev]'
pytest
```

## Status values
Circuit-CI returns one of:
- `AUTO_PASS`
- `HARD_FAIL`
- `CONFLICT_REQUIRES_REVIEW`
- `MISSING_DATA`
- `MARGINAL_REVIEW` (reserved for staging/measurement routing)

## Next
See `docs/` for architecture, pack authoring, and benchmarks.
