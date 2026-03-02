from __future__ import annotations

from typing import List

from ...core.engine import PackMeta, build_result
from ...core.schemas import CircuitState, Finding, ProposedChange, Severity

PACK = PackMeta(pack_id="electronics_psu", version="0.0.1")


def _get(state: CircuitState, part: str):
    return state.components.get(part)


def check_divider_resistor_dissipation(state: CircuitState) -> List[Finding]:
    """Catch classic divider-as-regulator mistakes: P = V^2 / R."""
    c = state.constraints
    if c.vin_v is None:
        return [Finding(rule_id="PSU_MISSING_VIN", severity=Severity.MISSING_DATA, message="vin_v required")]

    # Heuristic: if R1 and R2 exist and both are low ohms, compute dissipation at Vin.
    r1 = _get(state, "R1")
    r2 = _get(state, "R2")
    if not r1 or not r2:
        return []

    if r1.kind != "resistor" or r2.kind != "resistor":
        return []

    try:
        R = float(r1.value)
    except Exception:
        return []

    if R <= 0:
        return [Finding(rule_id="PSU_R1_INVALID", severity=Severity.HARD, message="R1 must be > 0")]

    P = (c.vin_v ** 2) / R
    maxp = r1.max_power_watts
    if maxp is not None and P > maxp:
        return [
            Finding(
                rule_id="PSU_RATING_RESISTOR_WATTAGE",
                severity=Severity.HARD,
                message=f"R1 dissipates {P:.2f}W > rated {maxp:.2f}W at Vin={c.vin_v}V",
                facts_used=["constraints.vin_v", "components.R1.value", "components.R1.max_power_watts"],
            )
        ]

    # If no rating given, route as missing data rather than pretending it's safe.
    if maxp is None and P > 0.25:
        return [
            Finding(
                rule_id="PSU_RESISTOR_WATTAGE_UNKNOWN",
                severity=Severity.MISSING_DATA,
                message=f"R1 dissipates ~{P:.2f}W; provide resistor wattage rating",
                facts_used=["constraints.vin_v", "components.R1.value"],
            )
        ]

    return []


def check_cap_voltage_rating(state: CircuitState) -> List[Finding]:
    c = state.constraints
    vout = c.target_v_out
    if vout is None:
        return []
    cap = _get(state, "COUT")
    if not cap or cap.kind != "capacitor":
        return []
    if cap.max_voltage is None:
        return [
            Finding(
                rule_id="PSU_CAP_VRATING_UNKNOWN",
                severity=Severity.MISSING_DATA,
                message="Output capacitor voltage rating missing",
                facts_used=["components.COUT"],
            )
        ]
    if cap.max_voltage < 1.25 * vout:
        return [
            Finding(
                rule_id="PSU_RATING_CAP_VOLTAGE",
                severity=Severity.HARD,
                message=f"COUT rated {cap.max_voltage}V < 1.25×Vout ({1.25*vout:.1f}V)",
                facts_used=["constraints.target_v_out", "components.COUT.max_voltage"],
            )
        ]
    return []


def lint(state: CircuitState, plan: ProposedChange | None = None):
    findings: List[Finding] = []
    findings += check_divider_resistor_dissipation(state)
    findings += check_cap_voltage_rating(state)
    return build_result(findings=findings, state_version=state.version, pack=PACK)
