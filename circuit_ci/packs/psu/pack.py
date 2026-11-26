from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from math import isfinite

from ...core.engine import PackMeta, RuleCheck, build_pack_result, missing
from ...core.schemas import CircuitState, Finding, LinterResult, ProposedChange, Severity

PACK = PackMeta(pack_id="electronics_psu", version="0.0.2")


def _positive(value: float | str | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if isfinite(number) and number > 0 else None


def _watts_text(power: Fraction) -> str:
    with localcontext() as context:
        context.prec = 18
        return format(Decimal(power.numerator) / Decimal(power.denominator), ".9g")


def check_divider_resistor_dissipation(state: CircuitState) -> RuleCheck:
    """Compare nominal ideal-series DC power with supplied applicable ratings."""
    evidence = state.rule_evidence.divider
    if evidence is None or state.netlist_graph:
        return missing(
            "PSU_DIVIDER_TOPOLOGY_UNKNOWN",
            "Require explicit ideal unloaded R1/R2 series topology across vin_v",
            "rule_evidence.divider",
        )
    vin = _positive(state.constraints.vin_v)
    if vin is None:
        return missing("PSU_MISSING_VIN", "Require finite positive vin_v", "constraints.vin_v")

    r1, r2 = state.components.get("R1"), state.components.get("R2")
    if (
        r1 is None
        or r2 is None
        or r1.part_id != "R1"
        or r2.part_id != "R2"
        or r1.kind != "resistor"
        or r2.kind != "resistor"
    ):
        return missing(
            "PSU_DIVIDER_COMPONENTS_UNKNOWN",
            "Require matching R1 and R2 resistor facts",
            "components.R1",
            "components.R2",
        )
    r1_ohm, r2_ohm = _positive(r1.value), _positive(r2.value)
    if r1_ohm is None or r2_ohm is None:
        return missing(
            "PSU_DIVIDER_RESISTANCE_INVALID",
            "Require finite positive R1 and R2 resistance in ohms",
            "components.R1.value",
            "components.R2.value",
        )

    # Treat stored numeric values as nominal decimal inputs. Rational
    # arithmetic avoids intermediate floating-point overflow/underflow.
    first, second = Fraction(str(r1_ohm)), Fraction(str(r2_ohm))
    current = Fraction(str(vin)) / (first + second)
    findings: list[Finding] = []
    complete = True
    for part, resistance in ((r1, first), (r2, second)):
        power = current * current * resistance
        rating = _positive(part.max_power_watts)
        facts = [
            "rule_evidence.divider.topology",
            "rule_evidence.divider.source",
            "constraints.vin_v",
            "components.R1.value",
            "components.R2.value",
            f"components.{part.part_id}.max_power_watts",
        ]
        if rating is None:
            complete = False
            findings.extend(
                missing(
                    "PSU_RESISTOR_WATTAGE_UNKNOWN",
                    f"{part.part_id}: require finite positive applicable power rating",
                    *facts,
                ).findings
            )
        elif power > Fraction(str(rating)):
            findings.append(
                Finding(
                    rule_id="PSU_RATING_RESISTOR_WATTAGE",
                    severity=Severity.HARD,
                    message=(
                        f"{part.part_id}: calculated nominal ideal DC power "
                        f"{_watts_text(power)} W > supplied rating {rating:g} W"
                    ),
                    facts_used=facts,
                )
            )
    return RuleCheck(complete, tuple(findings))


def check_cap_voltage_rating(state: CircuitState) -> RuleCheck:
    evidence = state.rule_evidence.output_cap
    if evidence is None:
        return missing(
            "PSU_CAP_VOLTAGE_UNKNOWN",
            "Require sourced steady DC voltage across COUT terminals, not target_v_out",
            "rule_evidence.output_cap",
        )
    cap = state.components.get("COUT")
    if cap is None or cap.kind != "capacitor" or cap.part_id != "COUT":
        return missing(
            "PSU_CAP_COMPONENT_UNKNOWN",
            "Require a matching COUT capacitor fact",
            "components.COUT",
        )
    rating = _positive(cap.max_voltage)
    facts = [
        "rule_evidence.output_cap.dc_voltage_v",
        "rule_evidence.output_cap.source",
        "components.COUT.max_voltage",
    ]
    if rating is None:
        return missing(
            "PSU_CAP_VRATING_UNKNOWN",
            "Require finite positive applicable DC voltage rating",
            *facts,
        )
    if evidence.dc_voltage_v > rating:
        return RuleCheck(
            True,
            (
                Finding(
                    rule_id="PSU_RATING_CAP_VOLTAGE",
                    severity=Severity.HARD,
                    message=(
                        f"COUT supplied steady DC voltage {evidence.dc_voltage_v:g} V "
                        f"> supplied rating {rating:g} V"
                    ),
                    facts_used=facts,
                ),
            ),
        )
    return RuleCheck(True)


def lint(state: CircuitState, plan: ProposedChange | None = None) -> LinterResult:
    return build_pack_result(
        state,
        PACK,
        (check_divider_resistor_dissipation(state), check_cap_voltage_rating(state)),
    )
