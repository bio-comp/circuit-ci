from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .schemas import AuditPacket, Finding, LinterResult, Severity, Status


@dataclass(frozen=True)
class PackMeta:
    pack_id: str
    version: str


def route_findings(findings: List[Finding]) -> Status:
    if any(f.severity == Severity.MISSING_DATA for f in findings):
        return Status.MISSING_DATA
    if any(f.severity == Severity.HARD for f in findings):
        return Status.HARD_FAIL
    if any(f.severity == Severity.CONFLICT for f in findings):
        return Status.CONFLICT_REQUIRES_REVIEW
    return Status.AUTO_PASS


def build_result(*, findings: List[Finding], state_version: str, pack: PackMeta) -> LinterResult:
    status = route_findings(findings)
    audit = AuditPacket(state_version=state_version, pack_id=pack.pack_id, pack_version=pack.version)
    return LinterResult(status=status, findings=findings, audit=audit)
