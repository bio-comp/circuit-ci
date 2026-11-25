from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Severity(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    CONFLICT = "CONFLICT"
    MISSING_DATA = "MISSING_DATA"


class Status(str, Enum):
    AUTO_PASS = "AUTO_PASS"
    HARD_FAIL = "HARD_FAIL"
    CONFLICT_REQUIRES_REVIEW = "CONFLICT_REQUIRES_REVIEW"
    MISSING_DATA = "MISSING_DATA"
    MARGINAL_REVIEW = "MARGINAL_REVIEW"  # soft findings require review


class ComponentFact(BaseModel):
    part_id: str
    kind: str  # resistor, capacitor, diode, regulator, opamp, etc.
    value: float | str
    tolerance_pct: Optional[float] = None
    max_voltage: Optional[float] = None
    max_current: Optional[float] = None
    max_power_watts: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("value", "max_voltage", "max_power_watts", mode="before")
    @classmethod
    def reject_boolean_electrical_values(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("boolean is not an electrical value")
        return value


class CircuitConstraints(BaseModel):
    vin_v: Optional[float] = None
    target_v_out: Optional[float] = None
    target_i_out: Optional[float] = None
    max_ripple_mv: Optional[float] = None
    # audio-ish
    target_gain_db: Optional[float] = None
    target_fc_hz: Optional[float] = None
    min_phase_margin_deg: Optional[float] = None

    @field_validator("vin_v", mode="before")
    @classmethod
    def reject_boolean_voltage(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("boolean is not a voltage")
        return value


class ScopedEvidence(BaseModel):
    """Caller-supplied, not independently authenticated, rule evidence."""

    model_config = ConfigDict(
        extra="forbid", strict=True, str_strip_whitespace=True, validate_assignment=True
    )
    source: str = Field(min_length=1)


class DividerEvidence(ScopedEvidence):
    topology: Literal["ideal_unloaded_series_r1_r2_across_vin"]


class OutputCapEvidence(ScopedEvidence):
    # Only a steady DC operating point, not a target or transient envelope.
    dc_voltage_v: float = Field(ge=0, allow_inf_nan=False)


class OpampEvidence(ScopedEvidence):
    # Scope: all required decoupling and DC bias-return paths of this op amp.
    decoupling: Literal["connected", "absent", "unknown"] = "unknown"
    decoupling_capacitors: list[str] = Field(default_factory=list)
    bias_return: Literal["present", "absent", "unknown"] = "unknown"


class RuleEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)
    divider: DividerEvidence | None = None
    output_cap: OutputCapEvidence | None = None
    opamps: dict[str, OpampEvidence] = Field(default_factory=dict)


class CircuitState(BaseModel):
    design_intent: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str  # caller-supplied deterministic hash of inputs

    constraints: CircuitConstraints = Field(default_factory=CircuitConstraints)
    components: Dict[str, ComponentFact] = Field(default_factory=dict)

    # minimal connectivity placeholder for v0
    # Later: pin-level connections and/or imported netlist
    netlist_graph: Dict[str, List[str]] = Field(default_factory=dict)

    missing_prerequisites: List[str] = Field(default_factory=list)
    rule_evidence: RuleEvidence = Field(default_factory=RuleEvidence)


class CircuitEdit(BaseModel):
    action: Literal["SET_VALUE", "SWAP_PART", "ADD_PART", "REWIRE"]
    target_part_id: str
    new_value: float | str | None = None
    params: Dict[str, Any] = Field(default_factory=dict)
    intent: Optional[str] = None


class ProposedChange(BaseModel):
    edits: List[CircuitEdit]


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    message: str
    facts_used: List[str] = Field(default_factory=list)


class AuditPacket(BaseModel):
    state_version: str
    pack_id: str
    pack_version: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class LinterResult(BaseModel):
    status: Status
    findings: List[Finding] = Field(default_factory=list)
    audit: AuditPacket


class MeasurementStep(BaseModel):
    step_id: str
    tool: str  # DMM, scope, function_generator
    setup: str
    stimulus: Optional[str] = None
    probe: str
    pass_condition: str
    fail_condition: str
    next_if_pass: Optional[str] = None
    next_if_fail: Optional[str] = None


class MeasurementPlan(BaseModel):
    plan_id: str
    goal: str
    steps: List[MeasurementStep]
