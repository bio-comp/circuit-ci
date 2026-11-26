"""Discriminating conditional-rule regressions, not physical qualification."""

from __future__ import annotations

from itertools import permutations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from circuit_ci.core.engine import (
    PackMeta,
    RuleCheck,
    build_pack_result,
    build_result,
    route_findings,
)
from circuit_ci.core.schemas import (
    CircuitConstraints,
    CircuitState,
    ComponentFact,
    DividerEvidence,
    Finding,
    OpampEvidence,
    OutputCapEvidence,
    RuleEvidence,
    Severity,
    Status,
)
from circuit_ci.packs.opamp.pack import lint as lint_opamp
from circuit_ci.packs.psu.pack import check_divider_resistor_dissipation
from circuit_ci.packs.psu.pack import lint as lint_psu


def state() -> CircuitState:
    return CircuitState(design_intent="synthetic example", version="test")


def divider_state(
    *,
    r1: float | str = 100.0,
    r2: float | str = 1000.0,
    p1: float | None = 0.012,
    p2: float | None = 0.25,
    vin: float | None = 12.0,
) -> CircuitState:
    result = state()
    result.constraints = CircuitConstraints(vin_v=vin, target_v_out=5.0)
    result.components = {
        "R1": ComponentFact(part_id="R1", kind="resistor", value=r1, max_power_watts=p1),
        "R2": ComponentFact(part_id="R2", kind="resistor", value=r2, max_power_watts=p2),
        "COUT": ComponentFact(part_id="COUT", kind="capacitor", value="470uF", max_voltage=16.0),
    }
    result.rule_evidence = RuleEvidence(
        divider=DividerEvidence(
            topology="ideal_unloaded_series_r1_r2_across_vin",
            source="synthetic ideal DC circuit",
        ),
        output_cap=OutputCapEvidence(dc_voltage_v=120 / 11, source="synthetic DC terminal voltage"),
    )
    return result


def opamp_state() -> CircuitState:
    result = state()
    result.design_intent = "AC-coupled buffer"
    result.components = {
        "U1": ComponentFact(part_id="U1", kind="opamp", value="OPA1656"),
        "CDEC": ComponentFact(part_id="CDEC", kind="capacitor", value="100nF"),
        "RBIAS": ComponentFact(part_id="RBIAS", kind="resistor", value=100000.0),
    }
    result.rule_evidence = RuleEvidence(
        opamps={
            "U1": OpampEvidence(
                source="synthetic reviewed connectivity",
                decoupling="connected",
                decoupling_capacitors=["CDEC"],
                bias_return="present",
            )
        }
    )
    return result


@pytest.mark.parametrize(
    ("severities", "complete", "expected"),
    [
        ([], False, Status.MISSING_DATA),
        ([], True, Status.AUTO_PASS),
        (
            [Severity.HARD, Severity.MISSING_DATA, Severity.CONFLICT, Severity.SOFT],
            False,
            Status.HARD_FAIL,
        ),
        ([Severity.HARD], True, Status.HARD_FAIL),
        ([Severity.CONFLICT, Severity.MISSING_DATA], True, Status.MISSING_DATA),
        ([Severity.CONFLICT, Severity.SOFT], True, Status.CONFLICT_REQUIRES_REVIEW),
        ([Severity.SOFT], True, Status.MARGINAL_REVIEW),
        ([Severity.SOFT], False, Status.MISSING_DATA),
    ],
)
def test_aggregation_precedence_and_retention(
    severities: list[Severity],
    complete: bool,
    expected: Status,
) -> None:
    for order in permutations(severities):
        findings = [
            Finding(rule_id=f"r{i}", severity=s, message=s.value) for i, s in enumerate(order)
        ]
        assert route_findings(findings, coverage_complete=complete) == expected
        result = build_result(
            findings=findings,
            state_version="test",
            pack=PackMeta("test", "0"),
            coverage_complete=complete,
        )
        assert result.status == expected
        assert result.findings[: len(findings)] == findings
        assert len(result.findings) == len(findings) + int(
            not complete and Severity.MISSING_DATA not in order
        )


def test_empty_pack_and_explicit_coverage() -> None:
    pack = PackMeta("test", "0")
    assert route_findings([]) == Status.MISSING_DATA
    assert build_pack_result(state(), pack, ()).status == Status.MISSING_DATA
    assert build_pack_result(state(), pack, (RuleCheck(False),)).status == Status.MISSING_DATA
    assert build_pack_result(state(), pack, (RuleCheck(True),)).status == Status.AUTO_PASS
    assert lint_psu(state()).status == Status.MISSING_DATA
    assert lint_opamp(state()).status == Status.MISSING_DATA


def test_ideal_divider_correct_power_and_supported_clean() -> None:
    clean = divider_state()
    assert check_divider_resistor_dissipation(clean) == RuleCheck(True)
    assert lint_psu(clean).status == Status.AUTO_PASS
    overstress = divider_state(p1=0.0119)
    result = lint_psu(overstress)
    assert result.status == Status.HARD_FAIL
    assert len(result.findings) == 1
    assert "0.0119008264 W" in result.findings[0].message
    assert "components.R2.value" in result.findings[0].facts_used
    assert "rule_evidence.divider.source" in result.findings[0].facts_used


def test_confirmed_r2_overstress_with_missing_r1_rating() -> None:
    result = lint_psu(divider_state(p1=None, p2=0.1))
    assert result.status == Status.HARD_FAIL
    assert [finding.severity for finding in result.findings] == [
        Severity.MISSING_DATA,
        Severity.HARD,
    ]
    assert "R2:" in result.findings[1].message


def test_both_resistors_overstress() -> None:
    result = lint_psu(divider_state(p1=0.001, p2=0.001))
    assert result.status == Status.HARD_FAIL
    assert len(result.findings) == 2
    assert [f.message.split(":")[0] for f in result.findings] == ["R1", "R2"]


def test_unknown_topology_does_not_calculate() -> None:
    sample = divider_state(p1=0.001)
    sample.rule_evidence.divider = None
    result = lint_psu(sample)
    assert result.status == Status.MISSING_DATA
    assert [f.rule_id for f in result.findings] == ["PSU_DIVIDER_TOPOLOGY_UNKNOWN"]
    assert not any("power" in f.message for f in result.findings)


@pytest.mark.parametrize("bad", [None, 0.0, -1.0, float("nan"), float("inf"), -float("inf")])
def test_invalid_input_voltage(bad: float | None) -> None:
    result = lint_psu(divider_state(vin=bad))
    assert result.status == Status.MISSING_DATA
    assert result.findings[0].rule_id == "PSU_MISSING_VIN"


@pytest.mark.parametrize(
    "bad", [0.0, -1.0, float("nan"), float("inf"), "100k", "bad", "1e999", "1e-999"]
)
@pytest.mark.parametrize("part", ["R1", "R2"])
def test_invalid_resistance(bad: float | str, part: str) -> None:
    sample = divider_state()
    sample.components[part].value = bad
    result = lint_psu(sample)
    assert result.status == Status.MISSING_DATA
    assert result.findings[0].rule_id == "PSU_DIVIDER_RESISTANCE_INVALID"


@pytest.mark.parametrize("bad", [None, 0.0, -1.0, float("nan"), float("inf")])
def test_invalid_power_rating(bad: float | None) -> None:
    result = lint_psu(divider_state(p1=bad))
    assert result.status == Status.MISSING_DATA
    assert result.findings[0].rule_id == "PSU_RESISTOR_WATTAGE_UNKNOWN"


@pytest.mark.parametrize("part", ["R1", "R2"])
@pytest.mark.parametrize("defect", ["missing", "wrong_kind", "wrong_id"])
def test_missing_or_mismatched_divider_component(part: str, defect: str) -> None:
    sample = divider_state()
    if defect == "missing":
        del sample.components[part]
    elif defect == "wrong_kind":
        sample.components[part].kind = "capacitor"
    else:
        sample.components[part].part_id = "other"
    result = lint_psu(sample)
    assert result.status == Status.MISSING_DATA
    assert result.findings[0].rule_id == "PSU_DIVIDER_COMPONENTS_UNKNOWN"


def test_exact_rating_boundary_and_extreme_inputs() -> None:
    # 2 V, 1+1 ohm: exactly 1 W each, no violation at rating.
    assert lint_psu(divider_state(r1=1, r2=1, vin=2, p1=1, p2=1)).status == Status.AUTO_PASS
    # Intermediate squares/sums overflow floats, but nominal rational power stays finite.
    assert (
        lint_psu(divider_state(r1=1e308, r2=1e308, vin=1e308, p1=1e308, p2=1e308)).status
        == Status.AUTO_PASS
    )
    assert (
        lint_psu(divider_state(r1=1e-300, r2=1e-300, vin=1e300, p1=1e300, p2=1e300)).status
        == Status.HARD_FAIL
    )


@given(
    r1=st.integers(min_value=1, max_value=10000),
    r2=st.integers(min_value=1, max_value=10000),
    vin=st.integers(min_value=1, max_value=100),
)
def test_divider_rating_order_metamorphic(r1: int, r2: int, vin: int) -> None:
    # At fixed current, the larger resistance dissipates at least as much.
    # Choose a rating between the independently computed powers, away from rounding boundaries.
    i = vin / (r1 + r2)
    p1, p2 = i**2 * r1, i**2 * r2
    low, high = sorted((p1, p2))
    if low == high:
        return
    midpoint = (low + high) / 2
    result = lint_psu(divider_state(r1=r1, r2=r2, vin=vin, p1=midpoint, p2=midpoint))
    assert result.status == Status.HARD_FAIL
    assert len(result.findings) == 1
    assert result.findings[0].message.startswith("R1:" if r1 > r2 else "R2:")


def test_cap_rating_uses_terminal_dc_not_target_and_no_arbitrary_derating() -> None:
    sample = divider_state()
    sample.constraints.target_v_out = 1000
    sample.rule_evidence.output_cap = OutputCapEvidence(dc_voltage_v=15, source="synthetic DC")
    assert lint_psu(sample).status == Status.AUTO_PASS
    sample.rule_evidence.output_cap = OutputCapEvidence(dc_voltage_v=17, source="synthetic DC")
    sample.rule_evidence.divider = None
    result = lint_psu(sample)
    assert result.status == Status.HARD_FAIL
    assert [f.severity for f in result.findings] == [Severity.MISSING_DATA, Severity.HARD]
    assert result.findings[1].rule_id == "PSU_RATING_CAP_VOLTAGE"
    sample.rule_evidence.output_cap = None
    assert lint_psu(sample).status == Status.MISSING_DATA


@pytest.mark.parametrize("bad", [None, 0.0, -1.0, float("nan"), float("inf")])
def test_cap_invalid_rating(bad: float | None) -> None:
    sample = divider_state()
    sample.components["COUT"].max_voltage = bad
    assert lint_psu(sample).findings[0].rule_id == "PSU_CAP_VRATING_UNKNOWN"
    assert lint_psu(sample).status == Status.MISSING_DATA


@pytest.mark.parametrize("defect", ["missing", "wrong_kind", "wrong_id"])
def test_cap_missing_component(defect: str) -> None:
    sample = divider_state()
    if defect == "missing":
        del sample.components["COUT"]
    elif defect == "wrong_kind":
        sample.components["COUT"].kind = "resistor"
    else:
        sample.components["COUT"].part_id = "other"
    assert lint_psu(sample).status == Status.MISSING_DATA
    assert lint_psu(sample).findings[0].rule_id == "PSU_CAP_COMPONENT_UNKNOWN"


def test_opamp_named_parts_are_not_connectivity() -> None:
    sample = opamp_state()
    sample.rule_evidence = RuleEvidence()
    result = lint_opamp(sample)
    assert result.status == Status.MISSING_DATA
    assert [f.rule_id for f in result.findings] == [
        "OPAMP_BIAS_RETURN_UNKNOWN",
        "OPAMP_DECOUPLING_UNKNOWN",
    ]
    sample.netlist_graph = {"CDEC": [], "RBIAS": []}
    assert lint_opamp(sample).status == Status.MISSING_DATA


def test_opamp_supported_clean_and_confirmed_disconnected() -> None:
    sample = opamp_state()
    assert lint_opamp(sample).status == Status.AUTO_PASS
    evidence = sample.rule_evidence.opamps["U1"]
    evidence.decoupling = "absent"
    evidence.decoupling_capacitors = []
    result = lint_opamp(sample)
    assert result.status == Status.CONFLICT_REQUIRES_REVIEW
    assert [f.rule_id for f in result.findings] == ["OPAMP_DECOUPLING_MISSING"]
    evidence.bias_return = "absent"
    evidence.decoupling = "unknown"
    result = lint_opamp(sample)
    assert result.status == Status.HARD_FAIL
    assert [f.severity for f in result.findings] == [Severity.HARD, Severity.MISSING_DATA]


@pytest.mark.parametrize("caps", [[], ["missing"], ["RBIAS"]])
def test_opamp_positive_requires_capacitor_facts(caps: list[str]) -> None:
    sample = opamp_state()
    sample.rule_evidence.opamps["U1"].decoupling_capacitors = caps
    assert lint_opamp(sample).status == Status.MISSING_DATA


def test_opamp_all_devices_and_findings_deterministic() -> None:
    sample = opamp_state()
    sample.components["U0"] = ComponentFact(part_id="U0", kind="opamp", value="synthetic")
    sample.rule_evidence.opamps["U1"].bias_return = "absent"
    result = lint_opamp(sample)
    assert result.status == Status.HARD_FAIL
    assert [f.rule_id for f in result.findings] == [
        "OPAMP_BIAS_RETURN_UNKNOWN",
        "OPAMP_INPUT_BIAS_RETURN_MISSING",
        "OPAMP_DECOUPLING_UNKNOWN",
    ]
    sample.components = dict(reversed(list(sample.components.items())))
    assert lint_opamp(sample).findings == result.findings
    sample.components["U1"].part_id = "wrong"
    assert lint_opamp(sample).status == Status.MISSING_DATA


def test_opamp_evidence_for_unknown_device() -> None:
    sample = opamp_state()
    sample.rule_evidence.opamps["U99"] = sample.rule_evidence.opamps["U1"]
    assert lint_opamp(sample).status == Status.MISSING_DATA


def test_state_prerequisites_and_untyped_graph_block_approval() -> None:
    sample = divider_state()
    sample.missing_prerequisites = ["load conditions", "temperature"]
    assert lint_psu(sample).status == Status.MISSING_DATA
    assert len(lint_psu(sample).findings) == 2
    sample.components["R1"].max_power_watts = 0.001
    assert lint_psu(sample).status == Status.HARD_FAIL
    sample.netlist_graph = {"R1": ["unknown"]}
    assert lint_psu(sample).status == Status.MISSING_DATA
    assert any(f.rule_id == "STATE_NETLIST_UNSUPPORTED" for f in lint_psu(sample).findings)
    opamp = opamp_state()
    opamp.netlist_graph = {"CDEC": []}
    assert lint_opamp(opamp).status == Status.MISSING_DATA


@pytest.mark.parametrize(
    "data",
    [
        {"constraints": {"vin_v": True}},
        {"components": {"R1": {"part_id": "R1", "kind": "resistor", "value": True}}},
        {
            "components": {
                "R1": {"part_id": "R1", "kind": "resistor", "value": 1, "max_power_watts": True}
            }
        },
        {
            "components": {
                "COUT": {
                    "part_id": "COUT",
                    "kind": "capacitor",
                    "value": "1uF",
                    "max_voltage": False,
                }
            }
        },
        {"rule_evidence": {"divider": {"topology": "loaded", "source": "fixture"}}},
        {
            "rule_evidence": {
                "divider": {"topology": "ideal_unloaded_series_r1_r2_across_vin", "source": " "}
            }
        },
        {"rule_evidence": {"output_cap": {"dc_voltage_v": float("nan"), "source": "fixture"}}},
        {"rule_evidence": {"output_cap": {"dc_voltage_v": -1, "source": "fixture"}}},
        {"rule_evidence": {"output_cap": {"dc_voltage_v": True, "source": "fixture"}}},
        {"rule_evidence": {"opamps": {"U1": {"source": "fixture", "bias_return": True}}}},
        {"rule_evidence": {"unsupported": True}},
    ],
)
def test_malformed_evidence_rejected(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CircuitState.model_validate({"design_intent": "fixture", "version": "test", **data})


def test_conflicting_decoupling_declaration_is_incomplete() -> None:
    sample = opamp_state()
    sample.rule_evidence.opamps["U1"].decoupling = "absent"
    assert lint_opamp(sample).status == Status.MISSING_DATA


def test_direct_cap_overstress_preserved_with_unsupported_graph() -> None:
    sample = divider_state()
    sample.netlist_graph = {"R1": ["unknown"]}
    sample.rule_evidence.output_cap = OutputCapEvidence(dc_voltage_v=17, source="synthetic DC")
    result = lint_psu(sample)
    assert result.status == Status.HARD_FAIL
    assert [f.severity for f in result.findings] == [
        Severity.MISSING_DATA,
        Severity.HARD,
        Severity.MISSING_DATA,
    ]


def test_evidence_assignment_validation() -> None:
    sample = divider_state()
    evidence = sample.rule_evidence.output_cap
    assert evidence is not None
    with pytest.raises(ValidationError):
        evidence.dc_voltage_v = float("nan")
    with pytest.raises(ValidationError):
        evidence.source = " "
    assert lint_psu(sample).status == Status.AUTO_PASS
