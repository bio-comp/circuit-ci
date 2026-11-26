import json
import subprocess
import sys
from pathlib import Path

import pytest

from circuit_ci.coverage_gate import main

EXAMPLES = Path(__file__).resolve().parents[1] / "benchmarks" / "coverage"
INPUTS = ("policy", "manifest", "receipts")


def args(root: Path) -> list[str]:
    return [value for name in INPUTS for value in (f"--{name}", str(root / f"{name}.json"))]


def test_published_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "circuit_ci.coverage_gate", *args(EXAMPLES)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {"status": "COVERAGE_MET", "findings": []}


@pytest.fixture
def packet(tmp_path: Path) -> Path:
    for name in INPUTS:
        (tmp_path / f"{name}.json").write_bytes((EXAMPLES / f"{name}.json").read_bytes())
    return tmp_path


@pytest.mark.parametrize(
    ("file", "field", "value", "code", "reason"),
    [
        ("manifest", "receipt_id", "invented", 1, "no independent receipt"),
        ("manifest", "body_sha256", "0" * 64, 1, "body digest mismatch"),
        ("manifest", "passage", "unobserved field", 1, "passage absent from preserved text"),
        ("manifest", "passage", None, 1, "passage absent from preserved text"),
        (
            "receipts",
            "subject",
            "same-family board",
            1,
            "receipt run, subject, revision or source mismatch",
        ),
        ("receipts", "revision", "A", 1, "receipt run, subject, revision or source mismatch"),
        ("receipts", "run_id", "old run", 1, "receipt run, subject, revision or source mismatch"),
        (
            "receipts",
            "source",
            "marketing page",
            1,
            "receipt run, subject, revision or source mismatch",
        ),
        ("receipts", "body_text", "different bytes", 2, ""),
        ("receipts", "body_text", None, 2, ""),
        ("manifest", "extra", True, 2, ""),
    ],
)
def test_record_mutations(
    packet: Path,
    capsys: pytest.CaptureFixture[str],
    file: str,
    field: str,
    value: str | bool | None,
    code: int,
    reason: str,
) -> None:
    path = packet / f"{file}.json"
    document = json.loads(path.read_text())
    document["evidence" if file == "manifest" else "receipts"][0][field] = value
    path.write_text(json.dumps(document))
    assert main(args(packet)) == code
    report = json.loads(capsys.readouterr().out)
    if reason:
        assert [f["reason"] for f in report["findings"]] == [reason]
    else:
        assert report["status"] == "INVALID_INPUT"


@pytest.mark.parametrize(
    "outcome", ["blocked", "negative_search", "partial", "citation_only", "self_reported"]
)
@pytest.mark.parametrize("file", ["manifest", "receipts"])
def test_unqualified_observations(
    packet: Path, file: str, outcome: str, capsys: pytest.CaptureFixture[str]
) -> None:
    path = packet / f"{file}.json"
    document = json.loads(path.read_text())
    row = document["evidence" if file == "manifest" else "receipts"][0]
    row["outcome"] = outcome
    path.write_text(json.dumps(document))
    assert main(args(packet)) == 1
    finding = json.loads(capsys.readouterr().out)["findings"][0]
    prefix = "manifest" if file == "manifest" else "collector"
    assert finding["reason"] == f"{prefix} outcome: {outcome}"


@pytest.mark.parametrize(
    ("file", "rows"), [("manifest", "evidence"), ("receipts", "receipts"), ("policy", "required")]
)
def test_duplicates_fail(packet: Path, file: str, rows: str) -> None:
    path = packet / f"{file}.json"
    doc = json.loads(path.read_text())
    doc[rows].append(doc[rows][0])
    path.write_text(json.dumps(doc))
    assert main(args(packet)) == 2


def test_supporting_eeprom_spec_cannot_replace_required_module_spec(
    packet: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = {"subject": "synthetic SO-DIMM", "revision": "J"}
    policy_path = packet / "policy.json"
    policy = json.loads(policy_path.read_text()) | run
    policy["required"] = [{"claim": "module supply", "source": "module sheet/J"}]
    policy_path.write_text(json.dumps(policy))
    manifest_path = packet / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) | run
    manifest["evidence"] = [
        manifest["evidence"][0] | {"claim": "module supply", "source": "EEPROM sheet/A"}
    ]
    manifest_path.write_text(json.dumps(manifest))
    receipt_path = packet / "receipts.json"
    receipts = json.loads(receipt_path.read_text())
    receipts["receipts"] = [receipts["receipts"][0] | run | {"source": "EEPROM sheet/A"}]
    receipt_path.write_text(json.dumps(receipts))
    assert main(args(packet)) == 1
    findings = json.loads(capsys.readouterr().out)["findings"]
    assert [(f["source"], f["reason"]) for f in findings] == [
        ("EEPROM sheet/A", "outside policy"),
        ("module sheet/J", "missing claim/source"),
    ]


def test_manifest_cannot_drop_claims(packet: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = packet / "manifest.json"
    doc = json.loads(path.read_text())
    doc["evidence"] = []
    path.write_text(json.dumps(doc))
    assert main(args(packet)) == 1
    assert len(json.loads(capsys.readouterr().out)["findings"]) == 2


def test_empty_policy_rejected(packet: Path) -> None:
    path = packet / "policy.json"
    doc = json.loads(path.read_text())
    doc["required"] = []
    path.write_text(json.dumps(doc))
    assert main(args(packet)) == 2


def test_stale_manifest_rejected(packet: Path) -> None:
    path = packet / "manifest.json"
    doc = json.loads(path.read_text())
    doc["run_id"] = "earlier"
    path.write_text(json.dumps(doc))
    assert main(args(packet)) == 2


@pytest.mark.parametrize("raw", [b'{"evidence":[],"evidence":[]}', b"{", b"\xff"])
def test_invalid_json(packet: Path, raw: bytes) -> None:
    (packet / "manifest.json").write_bytes(raw)
    assert main(args(packet)) == 2


def test_missing_file(packet: Path) -> None:
    (packet / "receipts.json").unlink()
    assert main(args(packet)) == 2
