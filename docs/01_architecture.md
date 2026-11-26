# Circuit-CI architecture: current v0 and proposed pipeline

## Existing modules (experimental, not design-qualified)

1. `circuit_ci/core/schemas.py` provides Pydantic data models for state,
   proposed edits, findings, audit packets, and measurement-plan **records**.
2. `circuit_ci/packs/{psu,opamp}/pack.py` provide deterministic checks
   under explicit, narrow evidence declarations; no schematic inference.
3. `circuit_ci/core/engine.py` preserves all findings and requires
   explicit rule coverage before approval.
4. `circuit_ci/cli/app.py` validates input state and emits JSON at the root
   `cci`/`circuitci` invocation. It currently returns process exit code 0
   for a valid execution even when the JSON verdict is `HARD_FAIL`; see
   [issue #12](https://github.com/bio-comp/circuit-ci/issues/12).

The `plan` argument of the rule-pack `lint` functions is currently ignored.
`staging/spice.py` and `telemetry/events.py` are **placeholders**, not
integration adapters. No physical measurement routing is implemented.

## Scoped rule evidence and status semantics

Both packs are version 0.0.2. Evaluation is conditional on validated
caller-supplied facts, not independently verified schematic or measurement
evidence. A nonempty source string identifies the caller's evidence;
Circuit-CI does not authenticate it or validate the caller's state hash.

Aggregate precedence: `HARD_FAIL` for any HARD finding; otherwise
`MISSING_DATA` for incomplete coverage or MISSING_DATA findings;
then `CONFLICT_REQUIRES_REVIEW` for CONFLICT; then `MARGINAL_REVIEW`
for SOFT; otherwise `AUTO_PASS` only after all mandatory checks complete.
No applicable/evaluated checks, unresolved `missing_prerequisites`, or
untyped `netlist_graph` prevent approval. The placeholder graph is not
interpreted; its presence also blocks topology-dependent calculations and
path declarations because their consistency cannot be established.
Direct COUT terminal-voltage evidence can still establish a conditional
rating violation independently of that graph.

### PSU pack

Both divider power and COUT DC voltage rating are mandatory for this narrow
pack. Unsupported/inapplicable cases remain MISSING_DATA; there is no
generic applicability waiver. An optional `rule_evidence.divider` declaration
requires the literal `ideal_unloaded_series_r1_r2_across_vin` topology and
a nonblank `source`. It asserts an ideal DC source across two series
resistors R1/R2, no other current path or load at the tap, and applicable
nominal resistance/power rating inputs. Names or design intent are not
evidence. For matching resistor facts and finite positive input voltage,
resistances in ohms, and applicable wattage ratings:

- I = Vin / (R1 + R2)
- P1 = I² R1; P2 = I² R2
- Each power is compared separately against its supplied rating; exceeding
  a rating is HARD, unknown/invalid rating is MISSING_DATA.

For 12 V, 100 ohms and 1000 ohms, P1 is about 0.0119008264 W and
P2 about 0.119008264 W. These are calculations, not measurements.
Resistance numbers or numeric strings are converted to finite positive
floats and evaluated as their nominal decimal representations using rational
arithmetic; tolerance, temperature derating, source/load variation and
transient analysis are not performed.

The `rule_evidence.output_cap` declaration supplies a finite nonnegative
steady DC voltage magnitude across COUT terminals (`dc_voltage_v`)
and source; `target_v_out` is not a terminal-voltage observation.
A matching COUT capacitor and finite positive applicable DC rating are
required. Voltage greater than that rating is HARD. The former universal
1.25 multiplier is removed: a derating policy requires part/conditions-specific
evidence. Polarity, ripple, transients, capacitance, ESR, lifetime and thermal
constraints are not evaluated.

### Op-amp pack

For each matching op-amp component, `rule_evidence.opamps` is keyed by
component ID. Each declaration requires a source and assessments of **all
required** supply decoupling and DC bias-return paths for that device:

- `decoupling` is `connected`, `absent` or `unknown`. Connected
  additionally requires a nonempty `decoupling_capacitors` list of
  matching capacitor IDs. Explicit absence of a required path is CONFLICT,
  not a universal hard rating violation.
- `bias_return` is `present`, `absent` or `unknown`. Explicit
  absence of a required DC return path is HARD. A return need not be a
  resistor named RBIAS. Unknown applicability or path coverage is MISSING_DATA.

A name, capacitor value, or free-text AC-coupling intent cannot establish
connectivity. These scoped assertions are not pin-level graph analysis or
qualification of decoupling values, layout, impedance, or bias performance.
An absent declaration cannot also name connected capacitors.

### Engineering basis and remaining contract

- [All About Circuits: series circuits](https://www.allaboutcircuits.com/textbook/direct-current/chpt-5/simple-series-circuits/)
  and [power equations](https://www.allaboutcircuits.com/textbook/direct-current/chpt-5/power-calculations/):
  series current and per-resistor Joule heating.
- [Murata: capacitor terminal voltage rating](https://www.murata.com/en-us/support/faqs/capacitor/ceramiccapacitor/char/0008):
  illustrates the distinction between applied voltage and rating for MLCCs;
  actual part specifications and operating conditions still control.
- [Analog Devices AN-937](https://www.analog.com/en/resources/app-notes/an-937.html)
  and [AN-581](https://www.analog.com/en/resources/app-notes/an-581.html):
  actual DC paths and supply decoupling matter, not labels or universal values.
  [Self-biasing amplifier example](https://www.analog.com/en/resources/design-notes/accoupled-amplifier-requires-no-dc-bias.html)
  demonstrates why a missing named external resistor alone is not a violation.

[Issue #3](https://github.com/bio-comp/circuit-ci/issues/3) owns versioned
pin/net connectivity, source provenance and rating/units validation,
applicability and operating envelopes, state/edit verification and timestamps.
The scoped declarations above are a limited interface, not a replacement
for that contract. A passed check does not establish physical acceptance.

## Target conceptual pipeline — not runnable today

1. `StateBuilder` would assemble a sourced, connectivity-aware
   `CircuitState` (**no StateBuilder implementation exists**).
2. `Proposer` would produce a typed `ProposedChange` (**no Proposer
   implementation or applying-edit engine exists**).
3. A future verifier would evaluate validated before/after changes and
   explicit applicability/coverage checks against sourced engineering rules.
4. A future decision layer would integrate the present fail-closed rule
   aggregation with qualified simulation and measurement evidence.
5. Optional SPICE execution and measured hardware observations would provide
   distinct simulation/physical evidence when safe and qualified.
6. A measurement planner might emit executable `MeasurementPlan` instructions
   when more evidence is required (**currently only a model/schema**).

Future EDA analysis should integrate a version-qualified KiCad Happy CLI
rather than recreate its general schematic parser. Product sourcing,
observability and physical testing remain separately scoped future work.
