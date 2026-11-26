# Circuit-CI — Agent Guidance

Applies to `bio-comp/circuit-ci` (Python package `circuit_ci`). This file sets **engineering boundaries**, not a duplicate backlog, specification, or session log. Scale checks to the change.

## Sources of authority

- **Implemented behavior:** current repository code, README/docs, tests, and exact GitHub Issue/PR revisions. A planned feature is not a shipped capability.
- **Inventory:** live Google Drive `electronics_lab_setup.md` (ID `1eoAN3o93C-16z64qaKK5SCB4OMo3Xf_i`) controls ownership, status, quantities, tools, and kit allocation.
- **Research:** live Drive `SOURCE_INDEX.md` (ID `1aq9dBhzZzAZbl-1AmY1jzcwMg3FY9Zi6`) routes sources; exact manufacturer documentation and applicable standards control consequential specifications. `PROJECT_CANONICAL_FILES.md` (ID `1vVVQUNZe_9UWPLld02ALrwI66AlIUcJm`) defines authority boundaries.
- **No fabricated state:** discussions and orders do not establish ownership; a source, datasheet, simulation, or marketing claim does not establish measured operation. Do not create competing canonicals or write purchases/inventory without authorization.

## Verification invariants

- Preserve typed `CircuitState`/`ProposedChange` validation, explicit verdict semantics, rule-pack/staging separation, and the interfaces actually present in the code.
- Given the same versioned inputs and evidence snapshot, results must be reproducible. Record freshness and provenance for changing inventory, prices, supplier data, and measurements.
- A hard failure remains a failure; missing critical data produces review/HOLD rather than a misleading pass. Do not weaken checks or goldens to make a change green. Golden regression parity is not proof of electrical correctness.
- Test material rules with positive and discriminating negative/missing-evidence cases. Report what a passing test really establishes.

## Feasibility before hardware implementation

For a proposed physical device or consequential hardware change:

1. **Requirements first:** intended functions, conditions, performance, safety, size, portability, budget, and falsifiable acceptance criteria.
2. **Qualified reuse first:** check usable **OWNED** inventory by exact part/quantity/condition and role; don't count ordered, unavailable, reserved, incompatible, or unverified stock. Bench instruments are not automatically part of the finished product.
3. **Exact compatibility:** maker/MPN/revision, power/logic levels, pinout, exposed peripherals, memory/PHY, SDK/driver/firmware maturity, debug and recovery. An MCU data-sheet feature does not qualify an arbitrary development board.
4. **Constructibility:** complete BOM and obtainable mating parts; PCB/fabrication and assembly; soldering/hot-air/microscope capability; interconnects, enclosure fit and access, power, ESD, thermal limits, and test equipment.
5. **Alternatives and cost:** compare realistic reuse-first, lowest incremental cash, and best lifecycle/staged options when viable. Include delivered cost, time, rework risk, kit opportunity cost, and upgrade value. Do not invent alternatives.
6. **Acceptance plan:** instruments, expected results, limits, known-good/known-bad controls, and physical measurements. Missing evidence on a critical axis blocks **BUILD_READY** for the affected scope.

Keep electrical feasibility, sourcing, mechanical/thermal readiness, and physical validation separate. Owning contracts: GitHub Issues [#5](https://github.com/bio-comp/circuit-ci/issues/5), [#6](https://github.com/bio-comp/circuit-ci/issues/6), [#7](https://github.com/bio-comp/circuit-ci/issues/7), [#16](https://github.com/bio-comp/circuit-ci/issues/16), and [#17](https://github.com/bio-comp/circuit-ci/issues/17).

## Evidence after implementation

- **Software tests/pack checks** prove the exercised software property; **ERC/DRC** checks specific structural rules; **simulation** covers stated models and conditions.
- **Sourcing/fit checks** establish time-scoped procurement and geometry evidence; **assembly inspection** covers observed workmanship; **bench tests** measure one physical hardware revision under documented setup and uncertainty.
- Never promote one level into another. Preserve source/revision, limitations, contradictory findings, negative controls, and next verification actions. **A user-built, measured device is the final physical acceptance**, not a prerequisite for closing bounded software-only work.

## Repository workflow

- **Issue first:** use existing Issue acceptance; branch/isolate changes; protect dirty worktrees and unrelated files. Store plans in Issues and evidence in PRs, not agent scratchpad directories.
- **Python/quality:** apply current Python Engineering SDLC and the repository's actual pinned environment. Use appropriate `uv`, Ruff, mypy, pytest/coverage, Hypothesis and domain checks **when established**. Do not treat code or tooling in unmerged PRs as part of the target branch, or prescribe outdated HTTP libraries, irrelevant dependencies or unverified build backends.
- **Before push:** verify the actual outgoing SHA with relevant non-mutating local checks; disclose missing/skipped checks. Retain independent CI, documentation audits and the accepted Zensical gate when integrated.
- **Review and integration:** independent review when required; no silent contract change, unsafe license change, merge, force reset, or branch cleanup. CI passing does not authorize merge. For provenance and license rules, verify the actual tracked files and the applicable accepted issue history (including [#1](https://github.com/bio-comp/circuit-ci/issues/1)).

## Repository-wide guidance

This `AGENTS.md` is a **tracked root repository file**. Keep its requirements consistent with accepted code, issue contracts, and current engineering standards; update it through reviewed repository changes, not private session notes. GitHub Issues/PRs—not `LOCAL_TODO.md` or duplicated session logs—are the durable engineering record.
