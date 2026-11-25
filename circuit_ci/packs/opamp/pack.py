from __future__ import annotations

from ...core.engine import PackMeta, RuleCheck, build_pack_result, missing
from ...core.schemas import CircuitState, Finding, LinterResult, ProposedChange, Severity

PACK = PackMeta(pack_id="electronics_opamp", version="0.0.2")


def _check_paths(state: CircuitState, *, bias: bool) -> RuleCheck:
    opamps = sorted(key for key, part in state.components.items() if part.kind == "opamp")
    if not opamps:
        return missing("OPAMP_APPLICABILITY_UNKNOWN", "No op-amp fact supplied", "components")
    findings: list[Finding] = []
    if state.netlist_graph:
        return missing(
            "OPAMP_CONNECTIVITY_UNSUPPORTED",
            "Cannot reconcile declarations with untyped netlist_graph",
            "netlist_graph",
        )
    complete = True
    for key in opamps:
        evidence = state.rule_evidence.opamps.get(key)
        field = "bias_return" if bias else "decoupling"
        path = f"rule_evidence.opamps.{key}"
        facts = [f"components.{key}", f"{path}.{field}", f"{path}.source"]
        if (
            state.components[key].part_id != key
            or evidence is None
            or (evidence.bias_return if bias else evidence.decoupling) == "unknown"
        ):
            complete = False
            findings.extend(
                missing(
                    "OPAMP_BIAS_RETURN_UNKNOWN" if bias else "OPAMP_DECOUPLING_UNKNOWN",
                    f"{key}: require explicit evidence of required {field} connectivity",
                    *facts,
                ).findings
            )
        elif (
            not bias
            and evidence.decoupling == "connected"
            and (
                not evidence.decoupling_capacitors
                or any(
                    (part := state.components.get(cap_id)) is None
                    or part.kind != "capacitor"
                    or part.part_id != cap_id
                    for cap_id in evidence.decoupling_capacitors
                )
            )
        ):
            complete = False
            findings.extend(
                missing(
                    "OPAMP_DECOUPLING_UNKNOWN",
                    f"{key}: connected declaration requires matching capacitor facts",
                    *facts,
                    f"{path}.decoupling_capacitors",
                ).findings
            )
        elif not bias and evidence.decoupling == "absent" and evidence.decoupling_capacitors:
            complete = False
            findings.extend(
                missing(
                    "OPAMP_DECOUPLING_UNKNOWN",
                    f"{key}: absent declaration contradicts connected capacitor identifiers",
                    *facts,
                    f"{path}.decoupling_capacitors",
                ).findings
            )
        elif (evidence.bias_return if bias else evidence.decoupling) == "absent":
            findings.append(
                Finding(
                    rule_id=(
                        "OPAMP_INPUT_BIAS_RETURN_MISSING" if bias else "OPAMP_DECOUPLING_MISSING"
                    ),
                    severity=Severity.HARD if bias else Severity.CONFLICT,
                    message=f"{key}: supplied evidence establishes absent required {field} path",
                    facts_used=facts,
                )
            )
    for key in sorted(state.rule_evidence.opamps.keys() - set(opamps)):
        complete = False
        findings.extend(
            missing(
                "OPAMP_APPLICABILITY_UNKNOWN",
                f"{key}: evidence has no matching op-amp fact",
                f"rule_evidence.opamps.{key}",
                "components",
            ).findings
        )
    return RuleCheck(complete, tuple(findings))


def check_missing_decoupling(state: CircuitState) -> RuleCheck:
    return _check_paths(state, bias=False)


def check_bias_return_present(state: CircuitState) -> RuleCheck:
    return _check_paths(state, bias=True)


def lint(state: CircuitState, plan: ProposedChange | None = None) -> LinterResult:
    return build_pack_result(
        state, PACK, (check_bias_return_present(state), check_missing_decoupling(state))
    )
