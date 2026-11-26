from __future__ import annotations

from dataclasses import dataclass

from .schemas import AuditPacket, CircuitState, Finding, LinterResult, Severity, Status


@dataclass(frozen=True)
class PackMeta:
    pack_id: str
    version: str


@dataclass(frozen=True)
class RuleCheck:
    """Explicit completion of a mandatory, narrowly scoped rule."""

    complete: bool
    findings: tuple[Finding, ...] = ()


def missing(rule_id: str, message: str, *facts: str) -> RuleCheck:
    return RuleCheck(
        complete=False,
        findings=(
            Finding(
                rule_id=rule_id,
                severity=Severity.MISSING_DATA,
                message=message,
                facts_used=list(facts),
            ),
        ),
    )


def route_findings(findings: list[Finding], *, coverage_complete: bool = False) -> Status:
    if any(f.severity == Severity.HARD for f in findings):
        return Status.HARD_FAIL
    if not coverage_complete or any(f.severity == Severity.MISSING_DATA for f in findings):
        return Status.MISSING_DATA
    if any(f.severity == Severity.CONFLICT for f in findings):
        return Status.CONFLICT_REQUIRES_REVIEW
    if any(f.severity == Severity.SOFT for f in findings):
        return Status.MARGINAL_REVIEW
    return Status.AUTO_PASS


def build_result(
    *,
    findings: list[Finding],
    state_version: str,
    pack: PackMeta,
    coverage_complete: bool = False,
) -> LinterResult:
    status = route_findings(findings, coverage_complete=coverage_complete)
    if not coverage_complete and not any(f.severity == Severity.MISSING_DATA for f in findings):
        findings = [
            *findings,
            *missing("PACK_COVERAGE_INCOMPLETE", "Required rule coverage incomplete").findings,
        ]
    audit = AuditPacket(
        state_version=state_version, pack_id=pack.pack_id, pack_version=pack.version
    )
    return LinterResult(status=status, findings=findings, audit=audit)


def build_pack_result(
    state: CircuitState, pack: PackMeta, checks: tuple[RuleCheck, ...]
) -> LinterResult:
    findings = [finding for check in checks for finding in check.findings]
    for prerequisite in state.missing_prerequisites:
        findings.extend(
            missing(
                "STATE_PREREQUISITE_MISSING",
                f"Unresolved prerequisite: {prerequisite}",
                "missing_prerequisites",
            ).findings
        )
    # The inherited graph has no typed pin/net meaning. Do not certify a
    # state whose supplied connectivity cannot be reconciled with declarations.
    if state.netlist_graph:
        findings.extend(
            missing(
                "STATE_NETLIST_UNSUPPORTED",
                "Untyped netlist_graph cannot establish or reconcile connectivity",
                "netlist_graph",
            ).findings
        )
    return build_result(
        findings=findings,
        state_version=state.version,
        pack=pack,
        coverage_complete=bool(checks) and all(check.complete for check in checks),
    )
