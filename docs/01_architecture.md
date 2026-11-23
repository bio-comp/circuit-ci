# Circuit-CI architecture: current v0 and proposed pipeline

## Existing modules (experimental, not design-qualified)

1. `circuit_ci/core/schemas.py` provides Pydantic data models for state,
   proposed edits, findings, audit packets, and measurement-plan **records**.
2. `circuit_ci/packs/{psu,opamp}/pack.py` provide simple deterministic
   checks. They rely on unverified assumptions: missing topology for
   resistor power, component-name proxies for op-amp connectivity.
3. `circuit_ci/core/engine.py` aggregates findings into a legacy status.
   Known defect: `MISSING_DATA` takes precedence over confirmed `HARD`,
   and no findings can yield `AUTO_PASS`. See [issue #2](https://github.com/bio-comp/circuit-ci/issues/2).
4. `circuit_ci/cli/app.py` validates input state and emits JSON at the root
   `cci`/`circuitci` invocation. It currently returns process exit code 0
   for a valid execution even when the JSON verdict is `HARD_FAIL`; see
   [issue #12](https://github.com/bio-comp/circuit-ci/issues/12).

The `plan` argument of the rule-pack `lint` functions is currently ignored.
`staging/spice.py` and `telemetry/events.py` are **placeholders**, not
integration adapters. No physical measurement routing is implemented.

## Target conceptual pipeline — not runnable today

1. `StateBuilder` would assemble a sourced, connectivity-aware
   `CircuitState` (**no StateBuilder implementation exists**).
2. `Proposer` would produce a typed `ProposedChange` (**no Proposer
   implementation or applying-edit engine exists**).
3. A future verifier would evaluate validated before/after changes and
   explicit applicability/coverage checks against sourced engineering rules.
4. A decision layer would preserve hard failures and identify unresolved
   evidence rather than treat missing checks as approval.
5. Optional SPICE execution and measured hardware observations would provide
   distinct simulation/physical evidence when safe and qualified.
6. A measurement planner might emit executable `MeasurementPlan` instructions
   when more evidence is required (**currently only a model/schema**).

Future EDA analysis should integrate a version-qualified KiCad Happy CLI
rather than recreate its general schematic parser. Product sourcing,
observability and physical testing remain separately scoped future work.
