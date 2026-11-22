from __future__ import annotations

from typing import List

from ...core.engine import PackMeta, build_result
from ...core.schemas import CircuitState, Finding, LinterResult, ProposedChange, Severity

PACK = PackMeta(pack_id="electronics_opamp", version="0.0.1")


def check_missing_decoupling(state: CircuitState) -> List[Finding]:
    """Heuristic: require at least one 100nF decoupling cap near op-amp rails."""
    # In v0 we just look for a part named CDEC.
    cdec = state.components.get("CDEC")
    if cdec is None:
        return [
            Finding(
                rule_id="OPAMP_DECOUPLING_MISSING",
                severity=Severity.CONFLICT,
                message="No decoupling capacitor found (expected CDEC ~100nF)",
                facts_used=["components"],
            )
        ]
    return []


def check_bias_return_present(state: CircuitState) -> List[Finding]:
    """Very rough v0 gate: if design_intent mentions AC-coupled input, require RBIAS."""
    if "ac" in state.design_intent.lower() and "coupl" in state.design_intent.lower():
        if "RBIAS" not in state.components:
            return [
                Finding(
                    rule_id="OPAMP_INPUT_BIAS_RETURN_MISSING",
                    severity=Severity.HARD,
                    message="AC-coupled input requires a bias return resistor (RBIAS)",
                    facts_used=["design_intent", "components"],
                )
            ]
    return []


def lint(state: CircuitState, plan: ProposedChange | None = None) -> LinterResult:
    findings: List[Finding] = []
    findings += check_bias_return_present(state)
    findings += check_missing_decoupling(state)
    return build_result(findings=findings, state_version=state.version, pack=PACK)
