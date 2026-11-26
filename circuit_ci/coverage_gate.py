"""Check research coverage against independently supplied policy and retrieval records."""

import argparse
import json
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(pattern=r"\S", min_length=1)]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Outcome = Literal[
    "body_read", "partial", "blocked", "negative_search", "citation_only", "self_reported"
]


class Record(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Run(Record):
    run_id: Text
    subject: Text
    revision: Text


class Requirement(Record):
    claim: Text
    source: Text

    @property
    def key(self) -> tuple[str, str]:
        return self.claim, self.source


class Policy(Run):
    schema_id: Literal["policy/v1"]
    required: Annotated[list[Requirement], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_requirements(self) -> Self:
        if len({item.key for item in self.required}) != len(self.required):
            raise ValueError("duplicate policy requirement")
        return self


class Citation(Requirement):
    outcome: Outcome
    receipt_id: Text | None = None
    body_sha256: Digest | None = None
    passage: Text | None = None


class Manifest(Run):
    schema_id: Literal["manifest/v1"]
    evidence: list[Citation]

    @model_validator(mode="after")
    def unique_claim_sources(self) -> Self:
        if len({item.key for item in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate claim and source")
        return self


class Receipt(Run):
    receipt_id: Text
    source: Text
    outcome: Outcome
    body_text: Text | None = None
    body_sha256: Digest | None = None

    @model_validator(mode="after")
    def check_preserved_text(self) -> Self:
        if self.outcome == "body_read":
            if self.body_text is None:
                raise ValueError("body_read requires preserved text")
            if sha256(self.body_text.encode("utf-8")).hexdigest() != self.body_sha256:
                raise ValueError("body digest differs from preserved UTF-8 text")
        return self


class CollectorLog(Record):
    schema_id: Literal["receipts/v1"]
    receipts: list[Receipt]

    @model_validator(mode="after")
    def unique_receipts(self) -> Self:
        if len({item.receipt_id for item in self.receipts}) != len(self.receipts):
            raise ValueError("duplicate receipt ID")
        return self


class Finding(Requirement):
    reason: str


class Report(Record):
    status: Literal["COVERAGE_MET", "COVERAGE_INCOMPLETE", "INVALID_INPUT"]
    findings: list[Finding]


def match_run(expected: Run, observed: Run) -> bool:
    return (expected.run_id, expected.subject, expected.revision) == (
        observed.run_id,
        observed.subject,
        observed.revision,
    )


def deficiency(
    policy: Policy, citation: Citation | None, receipts: dict[str, Receipt]
) -> str | None:
    if citation is None:
        return "missing claim/source"
    if citation.outcome != "body_read":
        return f"manifest outcome: {citation.outcome}"
    receipt = receipts.get(citation.receipt_id or "")
    if receipt is None:
        return "no independent receipt"
    if not match_run(policy, receipt) or receipt.source != citation.source:
        return "receipt run, subject, revision or source mismatch"
    if receipt.outcome != "body_read":
        return f"collector outcome: {receipt.outcome}"
    if citation.body_sha256 != receipt.body_sha256:
        return "body digest mismatch"
    if citation.passage is None or citation.passage not in (receipt.body_text or ""):
        return "passage absent from preserved text"
    return None


def validate_coverage(policy: Policy, manifest: Manifest, log: CollectorLog) -> Report:
    if not match_run(policy, manifest):
        raise ValueError("manifest run, subject or revision differs from policy")
    citations = {item.key: item for item in manifest.evidence}
    required = {item.key for item in policy.required}
    receipts = {item.receipt_id: item for item in log.receipts}
    findings = [
        Finding(claim=claim, source=source, reason="outside policy")
        for claim, source in sorted(citations.keys() - required)
    ]
    for item in policy.required:
        reason = deficiency(policy, citations.get(item.key), receipts)
        if reason is not None:
            findings.append(Finding(claim=item.claim, source=item.source, reason=reason))
    return Report(status="COVERAGE_INCOMPLETE" if findings else "COVERAGE_MET", findings=findings)


def check_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(pairs) != len(result):
        raise ValueError("duplicate JSON property")
    return result


def read_input(path: Path) -> bytes:
    raw = path.read_bytes()
    # Pydantic's JSON parser accepts duplicate properties. Reject them before validation.
    json.loads(raw, object_pairs_hook=check_keys)
    return raw


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        policy = Policy.model_validate_json(read_input(args.policy))
        manifest = Manifest.model_validate_json(read_input(args.manifest))
        log = CollectorLog.model_validate_json(read_input(args.receipts))
        report = validate_coverage(policy, manifest, log)
    except (ValueError, OSError, RecursionError):
        # Avoid echoing source contents or local path details into CI logs.
        print(Report(status="INVALID_INPUT", findings=[]).model_dump_json())
        return 2
    print(report.model_dump_json())
    return 1 if report.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
