from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


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
    MARGINAL_REVIEW = "MARGINAL_REVIEW"  # reserved for staging-based uncertainty


class ComponentFact(BaseModel):
    part_id: str
    kind: str  # resistor, capacitor, diode, regulator, opamp, etc.
    value: float | str
    tolerance_pct: Optional[float] = None
    max_voltage: Optional[float] = None
    max_current: Optional[float] = None
    max_power_watts: Optional[float] = None
    notes: Optional[str] = None


class CircuitConstraints(BaseModel):
    vin_v: Optional[float] = None
    target_v_out: Optional[float] = None
    target_i_out: Optional[float] = None
    max_ripple_mv: Optional[float] = None
    # audio-ish
    target_gain_db: Optional[float] = None
    target_fc_hz: Optional[float] = None
    min_phase_margin_deg: Optional[float] = None


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
